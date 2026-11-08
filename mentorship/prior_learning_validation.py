"""Admin validation of recorded learning before competency; no model migration."""
from collections import defaultdict
from django.core.exceptions import ValidationError
from django.db import connections, router
from django.db.models import Q
from django.forms.models import BaseInlineFormSet
from .models import Mentorshipdetails, Mentorshipvisit, Staff


def _pair(row):
    return row['mentee_id'], row['topic_id']


def _earliest_learning(rows):
    first = {}
    for row in rows:
        pair, day = _pair(row), row['date']
        if row['ls'] and day and all(pair):
            if pair not in first or day < first[pair]:
                first[pair] = day
    return first


def _supported(row, first):
    day = first.get(_pair(row))
    return bool(day and row['date'] and day < row['date'])


def _history(pairs, using):
    if not pairs:
        return []
    by_person = defaultdict(set)
    for mid, tid in pairs:
        by_person[mid].add(tid)
    query = Q(pk__in=[])
    for mid, topics in by_person.items():
        query |= Q(menteename_id=mid, topicname_id__in=topics)
    rows = Mentorshipdetails.objects.using(using).filter(query).values(
        'pk', 'menteename_id', 'topicname_id', 'mentorshipvistfk_id',
        'mentorshipvistfk__visitdate', 'ls', 'pc', 'mc')
    return [{'id': r['pk'], 'mentee_id': r['menteename_id'],
        'topic_id': r['topicname_id'], 'visit_id': r['mentorshipvistfk_id'],
        'date': r['mentorshipvistfk__visitdate'],
        'ls': r['ls'], 'pc': r['pc'], 'mc': r['mc']} for r in rows]


def _lock_people(pairs, using):
    # Django admin POST change/delete views already wrap validation and saving
    # in one transaction. Serialize these supported admin operations by mentee.
    if pairs and connections[using].in_atomic_block:
        list(Staff.objects.using(using).select_for_update().filter(
            pk__in=sorted({mid for mid, _ in pairs})).order_by('pk').values_list('pk', flat=True))


def _newly_unsupported(before, after, excluded_visits=()):
    old_first, new_first = _earliest_learning(before), _earliest_learning(after)
    old = {r['id']: r for r in before}
    return [r for r in after if (r['pc'] or r['mc']) and r['visit_id'] not in excluded_visits
            and r['id'] in old and _supported(old[r['id']], old_first)
            and not _supported(r, new_first)]


class PriorLearningInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        day = getattr(self.instance, 'visitdate', None)
        if not day:
            return  # The parent form reports an invalid or missing visit date.
        using = self.instance._state.db or router.db_for_write(Mentorshipdetails)
        vid = self.instance.pk
        if vid and connections[using].in_atomic_block:
            list(Mentorshipvisit.objects.using(using).select_for_update().filter(pk=vid).values_list('pk', flat=True))
        originals = list(Mentorshipdetails.objects.using(using).filter(
            mentorshipvistfk_id=vid).values('pk', 'menteename_id', 'topicname_id', 'ls', 'pc', 'mc')) if vid else []
        original_ids = {r['pk'] for r in originals}
        # Preserve rows omitted from a tampered management form. Django does not
        # delete an omitted row, so it must still enter the prospective state.
        current = {r['pk']: {'id': r['pk'], 'mentee_id': r['menteename_id'],
            'topic_id': r['topicname_id'], 'visit_id': vid, 'date': day,
            'ls': r['ls'], 'pc': r['pc'], 'mc': r['mc'], 'form': None} for r in originals}
        pairs = {(r['menteename_id'], r['topicname_id']) for r in originals
                 if r['menteename_id'] and r['topicname_id']}
        for index, form in enumerate(self.forms):
            cleaned = getattr(form, 'cleaned_data', {})
            if not cleaned:
                continue
            submitted_id = cleaned.get(self.model._meta.pk.name)
            pk = getattr(submitted_id, 'pk', None)
            if pk is not None and pk not in original_ids:
                raise ValidationError('Please reload this visit. A detail row does not belong to this visit; nothing was saved.')
            if pk is not None:
                current.pop(pk, None)
            if cleaned.get('DELETE'):
                continue
            mentee, topic = cleaned.get('menteename'), cleaned.get('topicname')
            if not mentee or not topic:
                continue
            pair = (mentee.pk, topic.pk); pairs.add(pair)
            key = pk if pk is not None else f'new-{index}'
            current[key] = {'id': key, 'mentee_id': mentee.pk, 'topic_id': topic.pk,
                'visit_id': vid, 'date': day, 'ls': bool(cleaned.get('ls')),
                'pc': bool(cleaned.get('pc')), 'mc': bool(cleaned.get('mc')), 'form': form,
                'mentee': ' '.join(p for p in [mentee.firstname, mentee.lastname] if p),
                'topic': topic.name}
        _lock_people(pairs, using)
        before = _history(pairs, using)
        after = [r for r in before if not vid or r['visit_id'] != vid] + list(current.values())
        first = _earliest_learning(after)
        errors = False
        for row in current.values():
            if (row['pc'] or row['mc']) and not _supported(row, first):
                message = (
                    f"A previous Learning Session (LS) must be recorded for {row.get('mentee', 'this mentee')} "
                    f"on {row.get('topic', 'this topic')} before Patient Competent (PC) or Model Competent (MC) can be saved.\n\n"
                    "Please confirm the selected mentee, topic and visit date. If the learning session has already taken place, "
                    "check that it is recorded with a date earlier than this mentorship visit.")
                if row.get('form') is not None:
                    row['form'].add_error(None, message)
                errors = True
        if errors:
            raise ValidationError('Prior Learning Session Required. Please review the highlighted mentorship entries. Your changes have not been saved.', code='prior_learning_required')
        if _newly_unsupported(before, after, excluded_visits={vid}):
            raise ValidationError(
                'This change would leave an existing PC/MC record without an earlier learning session. '
                'Keep supporting LS on an earlier visit date, or review the affected competency records first. '
                'Check the mentee history in the dashboard. Nothing was saved.')


class PriorLearningVisitAdminMixin:
    def get_deleted_objects(self, objs, request):
        objects = list(objs)
        deleted, counts, permissions, protected = super().get_deleted_objects(objects, request)
        if not objects:
            return deleted, counts, permissions, protected
        using = objects[0]._state.db or router.db_for_write(type(objects[0]))
        ids = {obj.pk for obj in objects}
        if connections[using].in_atomic_block:
            list(Mentorshipvisit.objects.using(using).select_for_update().filter(pk__in=ids).order_by('pk').values_list('pk', flat=True))
        pairs = set(Mentorshipdetails.objects.using(using).filter(
            mentorshipvistfk_id__in=ids, ls=True).exclude(menteename_id=None).exclude(
            topicname_id=None).values_list('menteename_id', 'topicname_id'))
        _lock_people(pairs, using)
        before = _history(pairs, using)
        after = [r for r in before if r['visit_id'] not in ids]
        if _newly_unsupported(before, after):
            protected = list(protected) + [
                'Earlier learning sessions support existing PC/MC records. Keep those LS records or review the affected competency records before deleting this visit.']
        return deleted, counts, permissions, protected

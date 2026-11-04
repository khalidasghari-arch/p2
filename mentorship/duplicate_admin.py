"""Facility-scoped duplicate review. Add DuplicateMenteeAdminMixin to StaffAdmin."""
import hashlib
import json
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher

from django.contrib import messages
from django.contrib.admin.models import LogEntry, CHANGE, DELETION
from django.contrib.contenttypes.models import ContentType
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import IntegrityError, router, transaction
from django.db.models.deletion import Collector, ProtectedError, RestrictedError
from django.http import Http404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse

from .models import Staff, Mentorshipdetails, MenteeTopicStatus


def normalize(value):
    value = unicodedata.normalize('NFKC', str(value or '')).casefold()
    value = value.translate(str.maketrans({'ي': 'ی', 'ى': 'ی', 'ك': 'ک'}))
    return ''.join(c for c in value if c.isalnum())


def _similar(a, b, threshold=.85):
    return bool(a and b and (a == b or (
        min(len(a), len(b)) >= 4 and
        SequenceMatcher(None, a, b).ratio() >= threshold)))


def _identity(value):
    value = normalize(value)
    if value in {'na', 'none', 'unknown', 'notavailable', 'notentered', 'null'}:
        return ''
    if value and all(c == '0' for c in value):
        return ''
    return value


def match_reason(a, b):
    """Possible duplicates only; never compare across registered facilities."""
    if not a.hfname_id or a.hfname_id != b.hfname_id:
        return ''
    name_a = _identity(str(a.firstname or '') + ' ' + str(a.lastname or ''))
    name_b = _identity(str(b.firstname or '') + ' ' + str(b.lastname or ''))
    father_a, father_b = _identity(a.fathername), _identity(b.fathername)
    ta, tb = _identity(a.tazkiranumber), _identity(b.tazkiranumber)
    profession_a, profession_b = _identity(a.position), _identity(b.position)
    same_position_id = (getattr(a, 'position_id', None) is not None and
                        getattr(a, 'position_id', None) == getattr(b, 'position_id', None))
    name_match = _similar(name_a, name_b)
    father_match = _similar(father_a, father_b)
    profession_match = same_position_id or _similar(profession_a, profession_b, .90)
    exact_tazkira = bool(ta and ta == tb)
    # A possible mistyped ID needs supporting identity evidence.
    similar_tazkira = _similar(ta, tb, .90)
    if not (exact_tazkira or (name_match and (father_match or profession_match or similar_tazkira))):
        return ''
    findings = []
    for label, left, right, matched in (
        ('Name', name_a, name_b, name_match),
        ('Father name', father_a, father_b, father_match),
        ('Tazkira', ta, tb, similar_tazkira),
        ('Profession', profession_a, profession_b, profession_match),
    ):
        result = ('matching' if left == right or (label == 'Profession' and same_position_id)
                  else 'similar') if matched else ('missing' if not left or not right else 'differs')
        findings.append(label + ': ' + result)
    return 'Possible duplicate — ' + '; '.join(findings) + '. Verify identity.'


def snapshot(obj):
    return {f.attname: f.value_from_object(obj) for f in obj._meta.concrete_fields}


def json_text(value):
    return json.dumps(value, cls=DjangoJSONEncoder, sort_keys=True, ensure_ascii=False)


def related_inventory(obj):
    """Include hidden reverse FKs/M2M. Unknown relationships always block transfer."""
    rows = []
    for rel in obj._meta.get_fields(include_hidden=True):
        if not rel.auto_created or not rel.is_relation or rel.concrete:
            continue
        field = getattr(rel, 'field', None)
        if field is None or not (rel.one_to_many or rel.one_to_one):
            continue
        model = rel.related_model
        count = model._base_manager.filter(**{field.attname: obj.pk}).count()
        if count:
            supported = ((model is Mentorshipdetails and field.name == 'menteename') or
                         (model is MenteeTopicStatus and field.name == 'mentee'))
            rows.append({'model': model._meta.label, 'field': field.name,
                         'count': count, 'supported': supported})
    # GenericRelation and direct M2M are not safe to infer or move automatically.
    for field in [*obj._meta.private_fields, *obj._meta.many_to_many]:
        manager = getattr(obj, field.name, None)
        if hasattr(manager, 'count'):
            count = manager.count()
            if count:
                rows.append({'model': str(field.name), 'field': field.name,
                             'count': count, 'supported': False})
    return rows


def empty_delete_check(obj):
    """Collector also detects generic/cascading dependencies absent from previews."""
    collector = Collector(using=router.db_for_write(Staff))
    try:
        collector.collect([obj])
    except (ProtectedError, RestrictedError) as exc:
        raise ValidationError('Linked records remain. Deletion is blocked.') from exc
    if any(model is not type(obj) and objects for model, objects in collector.data.items()):
        raise ValidationError('Other linked records remain. Deletion is blocked.')
    if any(qs.exists() for qs in collector.fast_deletes):
        raise ValidationError('Other linked records remain. Deletion is blocked.')
    if any(o.pk != obj.pk for o in collector.data.get(type(obj), ())):
        raise ValidationError('Another staff record would be deleted. Operation blocked.')
    if collector.field_updates:
        raise ValidationError('Other linked records would be changed. Deletion is blocked.')


class DuplicateMenteeAdminMixin:
    change_list_template = 'admin/mentorship/staff/change_list.html'

    def duplicate_url(self):
        return reverse(f'{self.admin_site.name}:mentorship_staff_duplicates')

    def get_urls(self):
        return [path('duplicates/', self.admin_site.admin_view(self.duplicates_view),
                     name='mentorship_staff_duplicates')] + super().get_urls()

    def _allowed_pair(self, request, source_id, target_id, lock=False):
        qs = self.get_queryset(request)
        if lock:
            # Avoid FOR UPDATE on any nullable joins in a customized queryset.
            allowed_ids = qs.values('pk')
            qs = Staff._base_manager.filter(pk__in=allowed_ids).select_for_update()
        pair = {str(o.pk): o for o in qs.filter(pk__in=[source_id, target_id]).order_by('pk')}
        source, target = pair.get(str(source_id)), pair.get(str(target_id))
        if source is None or target is None:
            raise Http404('Mentee not found in your authorized roster.')
        if source.pk == target.pk or not source.hfname_id or source.hfname_id != target.hfname_id:
            raise ValidationError('Choose two different mentees registered in the same facility.')
        if not all(self.has_view_permission(request, o) for o in (source, target)):
            raise PermissionDenied
        # Historical records may be outside the current province. Do not expose them.
        if not request.user.is_superuser:
            from hiva.admin_utils import user_province
            province = user_province(request)
            province_id = getattr(province, 'id', province)
            history = Mentorshipdetails.objects.filter(menteename_id__in=[source.pk, target.pk])
            if province_id is None or history.exclude(
                mentorshipvistfk__facilityfk__districtfk__provincefk_id=province_id
            ).exists():
                raise PermissionDenied('A national administrator must review this history.')
        return source, target

    def _preview(self, source, target, lock=False):
        details = Mentorshipdetails._base_manager.filter(
            menteename_id__in=[source.pk, target.pk]).order_by('pk')
        statuses = MenteeTopicStatus._base_manager.filter(
            mentee_id__in=[source.pk, target.pk]).order_by('pk')
        if lock:
            details, statuses = details.select_for_update(), statuses.select_for_update()
        details, statuses = list(details), list(statuses)
        # Do not assume unknown status fields or a particular uniqueness scope.
        # A shared topic is treated as a conflict even when the DB permits both.
        target_topics = defaultdict(list)
        for row in statuses:
            if row.mentee_id == target.pk:
                target_topics[row.topic_id].append(row)
        conflicts = []
        for row in statuses:
            if row.mentee_id == source.pk and target_topics[row.topic_id]:
                matches = target_topics[row.topic_id]
                if len(matches) != 1:
                    raise ValidationError('Multiple destination statuses exist for one topic. Resolve these first.')
                conflicts.append({'source': row, 'target': matches[0],
                                  'source_json': json_text(snapshot(row)),
                                  'target_json': json_text(snapshot(matches[0]))})
        # Multiple source rows on the same topic would require a multi-way resolution.
        keys = [row.topic_id for row in statuses if row.mentee_id == source.pk]
        if len(keys) != len(set(keys)):
            raise ValidationError('Multiple source statuses exist for one topic. Resolve these first.')
        inventory = related_inventory(source)
        payload = {'source': snapshot(source), 'target': snapshot(target),
                   'details': [snapshot(o) for o in details],
                   'statuses': [snapshot(o) for o in statuses], 'inventory': inventory}
        digest = hashlib.sha256(json_text(payload).encode()).hexdigest()
        return dict(source=source, target=target, inventory=inventory, conflicts=conflicts,
                    source_details=sum(o.menteename_id == source.pk for o in details),
                    source_statuses=sum(o.mentee_id == source.pk for o in statuses),
                    has_history=bool(inventory), blocked=any(not x['supported'] for x in inventory),
                    payload=payload, digest=digest, details=details, statuses=statuses)

    def _require_write(self, request, source, target, preview, action):
        if not self.has_delete_permission(request, source):
            raise PermissionDenied
        if action == 'merge':
            if not all(self.has_change_permission(request, o) for o in (source, target)):
                raise PermissionDenied
            for model, count in ((Mentorshipdetails, preview['source_details']),
                                 (MenteeTopicStatus, preview['source_statuses'])):
                opts = model._meta
                if count and not request.user.has_perm(f'{opts.app_label}.change_{opts.model_name}'):
                    raise PermissionDenied
            if preview['conflicts']:
                opts = MenteeTopicStatus._meta
                if not request.user.has_perm(f'{opts.app_label}.delete_{opts.model_name}'):
                    raise PermissionDenied

    def _execute(self, request):
        try:
            token = signing.loads(request.POST.get('preview_token', ''),
                                  salt='mentee-duplicates', max_age=1800)
        except signing.BadSignature as exc:
            raise ValidationError('Preview expired or invalid. Open a fresh preview.') from exc
        action = request.POST.get('action')
        if action not in {'merge', 'delete_empty'} or request.POST.get('confirm') != 'yes':
            raise ValidationError('Review the preview and confirm the selected action.')
        if token.get('user') != str(request.user.pk):
            raise PermissionDenied
        with transaction.atomic():
            source, target = self._allowed_pair(request, token['source'], token['target'], lock=True)
            preview = self._preview(source, target, lock=True)
            if preview['digest'] != token['digest']:
                raise ValidationError('Records changed since preview. Review a fresh preview.')
            self._require_write(request, source, target, preview, action)
            if preview['blocked']:
                raise ValidationError('Unrecognized linked records exist. Transfer is blocked for review.')
            if action == 'delete_empty' and preview['has_history']:
                raise ValidationError('This mentee has history. Use transfer instead.')
            resolutions = {}
            if action == 'merge':
                for conflict in preview['conflicts']:
                    old, existing = conflict['source'], conflict['target']
                    choice = request.POST.get(f'conflict_{old.pk}')
                    if choice not in {'target', 'source'}:
                        raise ValidationError('Select which status to retain for every shared topic.')
                    resolutions[str(old.pk)] = {'retained': choice, 'target_status_id': existing.pk}
                    if choice == 'source':
                        for field in old._meta.concrete_fields:
                            if not field.primary_key and field.name != 'mentee':
                                setattr(existing, field.attname, getattr(old, field.attname))
                        existing.full_clean()
                        existing.save()
                    empty_delete_check(old)
                    old.delete()
                # Deleted conflicting status instances have pk=None.
                conflict_ids = set(resolutions)
                for row in preview['statuses']:
                    if row.mentee_id == source.pk and str(row.pk) not in conflict_ids and row.pk is not None:
                        row.mentee_id = target.pk
                        row.full_clean()
                        row.save()
                # Update only the mentee FK. Visit, date, mentor and LS/PC/MC remain unchanged.
                Mentorshipdetails._base_manager.filter(menteename_id=source.pk).update(menteename_id=target.pk)
            empty_delete_check(source)
            if related_inventory(source):
                raise ValidationError('Linked records remain. Nothing was committed.')
            audit = {'action': action, 'before': preview['payload'], 'status_resolutions': resolutions,
                     'kept_id': target.pk, 'removed_id': source.pk}
            content_type = ContentType.objects.get_for_model(Staff)
            LogEntry.objects.create(user_id=request.user.pk, content_type_id=content_type.pk,
                object_id=str(target.pk), object_repr=str(target)[:200], action_flag=CHANGE,
                change_message=json_text(audit))
            LogEntry.objects.create(user_id=request.user.pk, content_type_id=content_type.pk,
                object_id=str(source.pk), object_repr=str(source)[:200], action_flag=DELETION,
                change_message=f'Duplicate review: {action}; retained Staff ID {target.pk}. Full snapshot in retained record history.')
            source.delete()

    def duplicates_view(self, request):
        if not self.has_view_permission(request):
            raise PermissionDenied
        for model in (Mentorshipdetails, MenteeTopicStatus):
            opts = model._meta
            if not request.user.has_perm(f'{opts.app_label}.view_{opts.model_name}'):
                raise PermissionDenied
        error = ''
        if request.method == 'POST':
            try:
                self._execute(request)
            except (ValidationError, IntegrityError) as exc:
                error = ('; '.join(exc.messages) if isinstance(exc, ValidationError) else
                         'A database constraint prevented this operation. All changes were rolled back.')
            else:
                self.message_user(request, 'Duplicate review completed. History and audit trail saved.', messages.SUCCESS)
                return HttpResponseRedirect(self.duplicate_url())
        elif request.method != 'GET':
            raise PermissionDenied
        qs = self.get_queryset(request)
        facilities = list(qs.exclude(hfname_id=None).values('hfname_id', 'hfname__name').distinct().order_by('hfname__name'))
        selected = request.GET.get('facility', '')
        preview, candidates, roster = None, [], []
        if selected and selected.isdigit() and any(str(f['hfname_id']) == selected for f in facilities):
            roster = list(qs.filter(hfname_id=selected).select_related('position').order_by('firstname', 'pk'))
            # Bound fuzzy pair comparisons; manual pair review remains available above limit.
            if len(roster) <= 500:
                for index, a in enumerate(roster):
                    for b in roster[index + 1:]:
                        reason = match_reason(a, b)
                        if reason:
                            candidates.append({'a': a, 'b': b, 'reason': reason})
            else:
                error = error or 'More than 500 mentees: automatic matching is paused. Choose two IDs for manual review.'
            for person in roster:
                person.duplicate_links = sum(row['count'] for row in related_inventory(person))
        if request.GET.get('source') and request.GET.get('target'):
            try:
                source, target = self._allowed_pair(request, request.GET['source'], request.GET['target'])
                preview = self._preview(source, target)
                preview['token'] = signing.dumps({'source': str(source.pk), 'target': str(target.pk),
                    'user': str(request.user.pk), 'digest': preview['digest']}, salt='mentee-duplicates', compress=True)
            except (ValidationError, ValueError) as exc:
                error = '; '.join(exc.messages) if isinstance(exc, ValidationError) else 'Choose valid mentee IDs.'
        context = {**self.admin_site.each_context(request), 'opts': self.model._meta,
                   'title': 'Review duplicate mentees', 'facilities': facilities,
                   'selected': selected, 'roster': roster, 'candidates': candidates,
                   'preview': preview, 'review_error': error}
        return TemplateResponse(request, 'admin/mentorship/staff/duplicates.html', context)

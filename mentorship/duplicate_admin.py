"""Facility-scoped duplicate review. Add DuplicateMenteeAdminMixin to StaffAdmin."""
import hashlib
import json
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher

from django.contrib import messages
from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.contenttypes.models import ContentType
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import IntegrityError, router, transaction
from django.db.models.deletion import Collector, ProtectedError, RestrictedError
from django.http import Http404, HttpResponseRedirect
from django.utils import timezone
from django.db.models import Q, Count
from mentee_review.models import ReviewMerge, ReviewDecision
from mentee_review.querysets import archived_ids
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
                     name='mentorship_staff_duplicates'),
                path('duplicates/history/', self.admin_site.admin_view(self.merge_history_view),
                     name='mentorship_staff_merge_history')] + super().get_urls()

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
                   'statuses': [snapshot(o) for o in statuses], 'inventory': inventory,
                   'target_inventory': related_inventory(target)}
        digest = hashlib.sha256(json_text(payload).encode()).hexdigest()
        return dict(source=source, target=target, inventory=inventory, conflicts=conflicts,
                    source_details=sum(o.menteename_id == source.pk for o in details),
                    source_statuses=sum(o.mentee_id == source.pk for o in statuses),
                    has_history=bool(inventory), blocked=any(not x['supported'] for x in inventory),
                    payload=payload, digest=digest, details=details, statuses=statuses)

    def _view_permissions(self, request):
        if not self.has_view_permission(request):
            raise PermissionDenied
        for model in (Mentorshipdetails, MenteeTopicStatus):
            opts = model._meta
            if not request.user.has_perm(f'{opts.app_label}.view_{opts.model_name}'):
                raise PermissionDenied

    def _write_permissions(self, request, source, target, undo=False):
        permission = 'undo_merge' if undo else 'merge_mentees'
        if not request.user.has_perm('mentee_review.' + permission):
            raise PermissionDenied('You do not have permission for this operation.')
        if not all(self.has_change_permission(request, o) for o in (source, target)):
            raise PermissionDenied
        for model, verbs in ((Mentorshipdetails, ['change']), (MenteeTopicStatus, ['add', 'change', 'delete'])):
            opts = model._meta
            for verb in verbs:
                if not request.user.has_perm(f'{opts.app_label}.{verb}_{opts.model_name}'):
                    raise PermissionDenied

    def has_delete_permission(self, request, obj=None):
        # No ordinary admin deletion of archived Staff, including delete_selected.
        if obj is not None and ReviewMerge.objects.filter(active=True, source_id=obj.pk).exists():
            return False
        return super().has_delete_permission(request, obj)

    def _sign(self, request, state):
        return signing.dumps({**state, 'user': str(request.user.pk)}, salt='mentee-review-wizard', compress=True)

    def _unsign(self, request):
        try:
            state = signing.loads(request.POST.get('state', ''), salt='mentee-review-wizard', max_age=1800)
        except signing.BadSignature as exc:
            raise ValidationError('This review has expired. Choose the pair again to start a fresh review.') from exc
        if state.get('user') != str(request.user.pk):
            raise PermissionDenied
        if state.get('step') not in range(3, 8):
            raise ValidationError('Start from the facility selection.')
        return state

    def _different_statuses(self, preview):
        result = []
        for conflict in preview['conflicts']:
            left, right = conflict['source'], conflict['target']
            fields = [f for f in left._meta.concrete_fields if not f.primary_key and f.name != 'mentee'
                      and not getattr(f,'auto_now',False) and not getattr(f,'auto_now_add',False)]
            if any(getattr(left, f.attname) != getattr(right, f.attname) for f in fields):
                result.append(conflict)
        return result

    def _check_state(self, request, state, lock=False):
        source, target = self._allowed_pair(request, state['source'], state['target'], lock=lock)
        if str(source.hfname_id) != str(state['facility']):
            raise ValidationError('The selected facility changed. Start the review again.')
        preview = self._preview(source, target, lock=lock)
        if preview['digest'] != state['digest']:
            raise ValidationError('The records changed during review. Start a fresh review before applying anything.')
        return preview

    def _audit(self, request, obj, message):
        LogEntry.objects.create(user_id=request.user.pk,
            content_type_id=ContentType.objects.get_for_model(Staff).pk,
            object_id=str(obj.pk), object_repr=str(obj)[:200], action_flag=CHANGE,
            change_message=message)

    def _commit_merge(self, request, state):
        if not request.user.has_perm('mentee_review.merge_mentees'):
            raise PermissionDenied
        if not state.get('same_person') or len(state.get('verification', '').strip()) < 10:
            raise ValidationError('Confirm identity and record how you verified it.')
        if not all(request.POST.get(key) == 'yes' for key in ('confirm_identity', 'confirm_keep', 'confirm_history')):
            raise ValidationError('Check all three final confirmations before applying.')
        with transaction.atomic():
            if ReviewMerge.objects.filter(active=True, source_id=state['source']).exists():
                raise ValidationError('This record has already been archived. Check merge history.')
            preview = self._check_state(request, state, lock=True)
            source, target = preview['source'], preview['target']
            if ReviewMerge.objects.filter(active=True, source_id__in=[source.pk, target.pk]).exists():
                raise ValidationError('One of these records is already archived. Start a fresh review.')
            self._write_permissions(request, source, target)
            if preview['blocked']:
                raise ValidationError('Other linked records need administrator review. No changes were applied.')
            choices = state.get('choices', {})
            different = {str(c['source'].pk) for c in self._different_statuses(preview)}
            if set(choices) != different or any(v not in {'source','target'} for v in choices.values()):
                raise ValidationError('Resolve every different topic status before continuing.')
            before = json.loads(json_text(preview['payload']))
            # Archive original status rows in the ledger before removing collisions.
            conflict_ids = set()
            for conflict in preview['conflicts']:
                old, existing = conflict['source'], conflict['target']
                conflict_ids.add(old.pk)
                choice = choices.get(str(old.pk), 'target')  # Identical saved values need no question.
                if choice == 'source':
                    for field in old._meta.concrete_fields:
                        if not field.primary_key and field.name != 'mentee':
                            setattr(existing, field.attname, getattr(old, field.attname))
                    existing.full_clean()
                    # Preserve exact snapshot values, including dates controlled by auto_now.
                    type(existing)._base_manager.filter(pk=existing.pk).update(**{
                        f.attname:getattr(existing,f.attname) for f in existing._meta.concrete_fields
                        if not f.primary_key and f.name != 'mentee'})
                empty_delete_check(old)
                old.delete()
            for row in preview['statuses']:
                if row.pk is not None and row.mentee_id == source.pk and row.pk not in conflict_ids:
                    row.mentee_id = target.pk
                    row.full_clean()
                    MenteeTopicStatus._base_manager.filter(pk=row.pk).update(mentee_id=target.pk)
            Mentorshipdetails._base_manager.filter(menteename_id=source.pk).update(menteename_id=target.pk)
            if related_inventory(source):
                raise ValidationError('Some linked records remain. No changes were applied.')
            source.status = False
            Staff._base_manager.filter(pk=source.pk).update(status=False)
            source.refresh_from_db(); target.refresh_from_db()
            after = self._preview(source, target, lock=True)
            record = ReviewMerge.objects.create(source_id=source.pk, target_id=target.pk,
                facility_id=source.hfname_id, actor_id=request.user.pk, actor_name=request.user.get_username(),
                verification=state['verification'], before=before, after_digest=after['digest'], choices=choices)
            self._audit(request, target, f'Merge {record.pk}: history transferred from Staff {source.pk}. Duplicate archived. Undo available through merge history if unchanged.')
            self._audit(request, source, f'Merge {record.pk}: archived duplicate of Staff {target.pk}; original snapshots retained.')
            return record

    def _undo_pair(self, request, record, lock=False):
        qs = Staff._base_manager.all()
        if not request.user.is_superuser:
            from hiva.admin_utils import user_province
            province = user_province(request)
            province_id = getattr(province, 'id', province)
            qs = qs.filter(hfname__districtfk__provincefk_id=province_id) if province_id else qs.none()
        if lock:
            ids = qs.values('pk')
            qs = Staff._base_manager.filter(pk__in=ids).select_for_update()
        pair = {o.pk:o for o in qs.filter(pk__in=[record.source_id, record.target_id]).order_by('pk')}
        if len(pair) != 2:
            raise PermissionDenied('The original records are not both available in your authorized province.')
        source, target = pair[record.source_id], pair[record.target_id]
        if not request.user.is_superuser:
            history = Mentorshipdetails.objects.filter(menteename_id__in=pair)
            if history.exclude(mentorshipvistfk__facilityfk__districtfk__provincefk_id=province_id).exists():
                raise PermissionDenied('A national administrator must review this history.')
        return source, target

    def _undo_merge(self, request, merge_id):
        if not request.user.has_perm('mentee_review.undo_merge'):
            raise PermissionDenied
        with transaction.atomic():
            # Staff locks come first for all operations to avoid reverse lock ordering.
            record = ReviewMerge.objects.get(pk=merge_id)
            source, target = self._undo_pair(request, record, lock=True)
            record = ReviewMerge.objects.select_for_update().get(pk=merge_id)
            self._write_permissions(request, source, target, undo=True)
            if not record.active:
                raise ValidationError('This merge has already been undone.')
            overlap = Q(source_id__in=[source.pk,target.pk]) | Q(target_id__in=[source.pk,target.pk])
            if ReviewMerge.objects.filter(overlap, active=True, pk__gt=record.pk).exists():
                raise ValidationError('Undo the newer merge involving these mentees first.')
            current = self._preview(source,target,lock=True)
            if current['digest'] != record.after_digest:
                raise ValidationError('These records have changed since the merge. Automatic undo is blocked to protect later work. Ask the administrator to reconcile the history.')
            originals = record.before['statuses']
            # Reused primary keys outside the pair must never be overwritten.
            current_ids = {o.pk for o in current['statuses']}
            missing_ids = [row[MenteeTopicStatus._meta.pk.attname] for row in originals
                           if row[MenteeTopicStatus._meta.pk.attname] not in current_ids]
            if MenteeTopicStatus._base_manager.filter(pk__in=missing_ids).exists():
                raise ValidationError('An original status ID is now in use. Automatic undo is blocked.')
            def values(model, row):
                return {f.attname:f.to_python(row[f.attname]) for f in model._meta.concrete_fields}
            # Restore moved rows first, then recreate the archived shared-topic rows.
            for row in originals:
                data=values(MenteeTopicStatus,row);pk=data.pop(MenteeTopicStatus._meta.pk.attname)
                if pk in current_ids:
                    MenteeTopicStatus._base_manager.filter(pk=pk).update(**data)
            missing = [MenteeTopicStatus(**values(MenteeTopicStatus,row)) for row in originals
                       if row[MenteeTopicStatus._meta.pk.attname] in missing_ids]
            MenteeTopicStatus._base_manager.bulk_create(missing)
            for row in originals:
                data=values(MenteeTopicStatus,row);pk=data.pop(MenteeTopicStatus._meta.pk.attname)
                if pk in missing_ids:
                    MenteeTopicStatus._base_manager.filter(pk=pk).update(**data)
            for row in record.before['details']:
                Mentorshipdetails._base_manager.filter(pk=row[Mentorshipdetails._meta.pk.attname]).update(menteename_id=row['menteename_id'])
            Staff._base_manager.filter(pk=source.pk).update(status=record.before['source']['status'])
            source.refresh_from_db();target.refresh_from_db()
            restored=self._preview(source,target,lock=True)['payload']
            if json_text(restored) != json_text(record.before):
                raise ValidationError('Restoration verification failed. All undo changes were rolled back.')
            record.active=False;record.undone_at=timezone.now();record.undone_by=request.user.pk
            record.save(update_fields=['active','undone_at','undone_by'])
            self._audit(request,target,f'Merge {record.pk} undone. Original links and saved topic statuses restored.')
            self._audit(request,source,f'Merge {record.pk} undone. Original active status restored.')
            return record

    def _identity_rows(self, a, b):
        name=lambda o:' '.join(str(v) for v in (o.firstname,o.lastname) if v and str(v).lower()!='none') or 'Not entered'
        rows=[]
        for label,left,right in [('Name',name(a),name(b)),('Father name',a.fathername,b.fathername),
                                 ('Tazkira',a.tazkiranumber,b.tazkiranumber),('Profession',a.position,b.position)]:
            na,nb=_identity(left),_identity(right)
            result='Missing information' if not na or not nb else ('Matching' if na==nb else ('Similar' if _similar(na,nb) else 'Different'))
            rows.append({'label':label,'a':str(left or 'Not entered'),'b':str(right or 'Not entered'),'result':result})
        return rows

    def _status_card(self, conflict):
        left,right=conflict['source'],conflict['target']
        topic=getattr(left,'topic',None)
        label=getattr(topic,'name',None) or str(topic or f'Topic {left.topic_id}')
        rows=[]
        for f in left._meta.concrete_fields:
            if f.primary_key or f.name in {'mentee','topic'} or getattr(f,'auto_now',False) or getattr(f,'auto_now_add',False):
                continue
            def show(obj):
                display=getattr(obj,'get_'+f.name+'_display',None)
                value=display() if display else getattr(obj,f.attname)
                value={'IN_PROGRESS':'Learning in progress','COMPETENT':'Competent','LS':'Learning session','PC':'Patient competent','MC':'Model competent'}.get(str(value),value)
                return str(value) if value is not None and value!='' else 'Not recorded'
            labels={'consecutive_ls':'Consecutive learning sessions','competent_date':'Competency date',
                    'last_date':'Last recorded date','last_session_type':'Last session type','status':'Progress'}
            rows.append({'label':labels.get(f.name,str(f.verbose_name).replace('_',' ').capitalize()),'a':show(left),'b':show(right)})
        return {'id':str(left.pk),'topic':label,'rows':rows}

    def duplicates_view(self, request):
        self._view_permissions(request)
        error='';state=None;preview=None;step=1;outcome='';result=None
        selected=request.GET.get('facility','')
        if request.method=='POST':
            try:
                if request.POST.get('action')=='compare':
                    selected=request.POST.get('facility','')
                    source,target=self._allowed_pair(request,request.POST.get('left'),request.POST.get('right'))
                    if str(source.hfname_id)!=selected:
                        raise ValidationError('Choose two records in the selected facility.')
                    preview=self._preview(source,target)
                    state={'step':3,'source':str(source.pk),'target':str(target.pk),'facility':selected,
                           'digest':preview['digest'],'choices':{}}
                else:
                    state=self._unsign(request);preview=self._check_state(request,state)
                    selected=state['facility'];step=state['step'];action=request.POST.get('action')
                    if action=='back':
                        state['step']=max(3,step-1)
                        if step in (6,7): state['choices']={}
                    elif action=='continue':
                        if step==3:
                            decision=request.POST.get('identity')
                            note=request.POST.get('verification','').strip()
                            if decision in {'different','unsure'}:
                                ReviewDecision.objects.create(left_id=state['source'],right_id=state['target'],
                                    facility_id=selected,decision=decision,note=note,actor_id=request.user.pk)
                                outcome=('Marked as different people. No mentee or history records were changed.' if decision=='different'
                                         else 'Saved for identity verification. No mentee or history records were changed.')
                                state=None
                            elif decision=='same' and len(note)>=10:
                                state.update(same_person=True,verification=note,step=4)
                            else:
                                raise ValidationError('Choose an identity answer. For the same person, explain how you verified identity in at least 10 characters.')
                        elif step==4:
                            keep=request.POST.get('keep')
                            if keep not in (state['source'],state['target']):
                                raise ValidationError('Choose the correct record to keep.')
                            if keep==state['source']:
                                state['source'],state['target']=state['target'],state['source']
                                preview=self._preview(preview['target'],preview['source'])
                                state['digest']=preview['digest']
                            state.update(step=5,choices={})
                        elif step==5:
                            if preview['blocked']: raise ValidationError('Other linked records need administrator review. Cancel this review and request help.')
                            state['step']=6 if self._different_statuses(preview) else 7
                        elif step==6:
                            conflicts=self._different_statuses(preview)
                            remaining=[c for c in conflicts if str(c['source'].pk) not in state['choices']]
                            choice=request.POST.get('choice')
                            if choice=='help':
                                outcome='Review stopped for help with topic progress. No mentee or history records were changed.'
                                ReviewDecision.objects.create(left_id=state['source'],right_id=state['target'],facility_id=selected,
                                    decision='unsure',note='Topic progress needs mentor verification. '+state.get('verification',''),actor_id=request.user.pk)
                                state=None
                            elif remaining and choice in {'source','target'}:
                                state['choices'][str(remaining[0]['source'].pk)]=choice
                                if len(state['choices'])==len(conflicts):state['step']=7
                            else:raise ValidationError('Choose a status to keep, or select I need help.')
                        else:raise ValidationError('Use the final confirmation button to apply the change.')
                    elif action=='apply' and step==7:
                        result=self._commit_merge(request,state)
                        return HttpResponseRedirect(self.duplicate_url()+f'?result={result.pk}')
                    else:raise ValidationError('Use the buttons shown for the current step.')
            except (ValidationError,IntegrityError,ValueError,Staff.DoesNotExist) as exc:
                error='; '.join(exc.messages) if isinstance(exc,ValidationError) else 'No change was completed. Check the selected records and start a fresh review.'
        elif request.method!='GET':
            raise PermissionDenied
        qs=self.get_queryset(request).exclude(pk__in=archived_ids())
        facilities=list(qs.exclude(hfname_id=None).values('hfname_id','hfname__name').distinct().order_by('hfname__name'))
        roster=[];candidates=[];decisions=[]
        if state:
            step=state['step']
            # Recompute orientation-dependent display after the keep selection.
            try:preview=self._check_state(request,state)
            except (ValidationError,Http404):
                state=None;preview=None;step=1;error='Records changed or are no longer available. Start a fresh review.'
        elif not outcome:
            step=2 if selected and selected.isdigit() and any(str(f['hfname_id'])==selected for f in facilities) else 1
        if step==2:
            roster=list(qs.filter(hfname_id=selected).select_related('position').order_by('firstname','pk'))
            ids=[p.pk for p in roster]
            detail_counts=dict(Mentorshipdetails.objects.filter(menteename_id__in=ids).values_list('menteename_id').annotate(n=Count('pk')))
            status_counts=dict(MenteeTopicStatus.objects.filter(mentee_id__in=ids).values_list('mentee_id').annotate(n=Count('pk')))
            for person in roster:
                person.review_activity_count=detail_counts.get(person.pk,0)
                person.review_status_count=status_counts.get(person.pk,0)
            if len(roster)<=500:
                for i,a in enumerate(roster):
                    for b in roster[i+1:]:
                        reason=match_reason(a,b)
                        if reason:candidates.append({'a':a,'b':b,'reason':reason})
            else:error='This facility has over 500 mentees. Use the manual pair selection for review.'
            decisions=ReviewDecision.objects.filter(facility_id=selected).order_by('-pk')[:20]
        if request.GET.get('result','').isdigit():
            result=ReviewMerge.objects.filter(pk=request.GET['result']).first()
            if result:
                self._undo_pair(request,result)  # Also enforce province and history visibility.
                step=8
        context={**self.admin_site.each_context(request),'opts':self.model._meta,'title':'Guided mentee duplicate review',
                 'step':step,'facilities':facilities,'selected':selected,'roster':roster,'candidates':candidates,
                 'decisions':decisions,'review_error':error,'outcome':outcome,'result':result,
                 'can_merge':request.user.has_perm('mentee_review.merge_mentees'),'home_url':self.duplicate_url(),'history_url':reverse(f'{self.admin_site.name}:mentorship_staff_merge_history')}
        if state and preview:
            a,b=preview['source'],preview['target']
            different=self._different_statuses(preview)
            remaining=[c for c in different if str(c['source'].pk) not in state['choices']]
            summaries=[]
            for conflict in different:
                use_source=state['choices'].get(str(conflict['source'].pk))=='source'
                chosen=conflict['source'] if use_source else conflict['target']
                progress=getattr(chosen,'status','Not recorded')
                progress={'IN_PROGRESS':'Learning in progress','COMPETENT':'Competent'}.get(str(progress),str(progress))
                summaries.append({'topic':self._status_card(conflict)['topic'],'choice':progress+' — '+('use progress from record being archived' if use_source else 'keep progress of retained mentee')})
            context.update(state_token=self._sign(request,state),preview=preview,identity_rows=self._identity_rows(a,b),
                topic_card=self._status_card(remaining[0]) if remaining else None,topic_number=len(state['choices'])+1,
                topic_total=len(different),identical_topics=len(preview['conflicts'])-len(different),
                status_summaries=summaries,verification=state.get('verification',''))
        return TemplateResponse(request,'admin/mentorship/staff/duplicates.html',context)

    def merge_history_view(self, request):
        self._view_permissions(request)
        error='';notice='';confirm=None
        if request.method=='POST':
            try:
                if request.POST.get('confirm_undo')!='yes':raise ValidationError('Confirm that you want to restore the original records.')
                self._undo_merge(request,int(request.POST.get('merge_id','')))
                notice='Merge undone. Both original mentee records and their history links have been restored.'
            except (ValidationError,IntegrityError,ValueError,ReviewMerge.DoesNotExist) as exc:
                error='; '.join(exc.messages) if isinstance(exc,ValidationError) else 'Undo could not be completed. No partial restoration was saved.'
        elif request.method!='GET':raise PermissionDenied
        # Scope the list to records whose current Staff facilities are authorized.
        scope=Staff._base_manager.all()
        if not request.user.is_superuser:
            from hiva.admin_utils import user_province
            province=user_province(request);pid=getattr(province,'id',province)
            scope=scope.filter(hfname__districtfk__provincefk_id=pid) if pid else scope.none()
        records=ReviewMerge.objects.filter(source_id__in=scope.values('pk'),target_id__in=scope.values('pk')).order_by('-pk')
        visible=[]
        for record in records[:100]:
            try:self._undo_pair(request,record)
            except PermissionDenied:continue
            record.source_label=' '.join(str(record.before['source'].get(k) or '') for k in ('firstname','lastname')).strip()
            record.target_label=' '.join(str(record.before['target'].get(k) or '') for k in ('firstname','lastname')).strip()
            visible.append(record)
        if request.GET.get('undo','').isdigit():
            confirm=next((r for r in visible if str(r.pk)==request.GET['undo']),None)
            if not confirm:raise Http404
            if not request.user.has_perm('mentee_review.undo_merge'):raise PermissionDenied
        return TemplateResponse(request,'admin/mentorship/staff/merge_history.html',{
            **self.admin_site.each_context(request),'opts':self.model._meta,'title':'Mentee merge history',
            'records':visible,'confirm':confirm,'review_error':error,'notice':notice,
            'can_undo':request.user.has_perm('mentee_review.undo_merge'),'home_url':self.duplicate_url()})

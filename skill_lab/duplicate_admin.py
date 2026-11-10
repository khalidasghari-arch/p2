"""Guided same-facility skill lab duplicate review with archive and guarded undo."""
import hashlib
import json
import unicodedata
from difflib import SequenceMatcher

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
from skilllab_review.models import ReviewMerge, ReviewDecision
from skilllab_review.querysets import archived_ids
from django.template.response import TemplateResponse
from django.urls import path, reverse

from .models import Skill_Lab_Mentee, SkillLabParticipantRecord

Staff = Skill_Lab_Mentee
Record = SkillLabParticipantRecord


def normalize(value):
    value = unicodedata.normalize('NFKC', str(value or '')).casefold()
    value = value.translate(str.maketrans({'ي': 'ی', 'ى': 'ی', 'ك': 'ک'}))
    return ''.join(str(unicodedata.decimal(c)) if c.isdecimal() else c for c in value if c.isalnum())


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
            supported = model is Record and field.name == 'mentee_name'
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


class SkillLabDuplicateMenteeAdminMixin:
    change_list_template = 'admin/skill_lab/skill_lab_mentee/change_list_review.html'

    def duplicate_url(self):
        return reverse(f'{self.admin_site.name}:skill_lab_skill_lab_mentee_duplicates')

    def get_urls(self):
        return [path('duplicates/', self.admin_site.admin_view(self.duplicates_view),
                     name='skill_lab_skill_lab_mentee_duplicates'),
                path('duplicates/history/', self.admin_site.admin_view(self.merge_history_view),
                     name='skill_lab_skill_lab_mentee_merge_history')] + super().get_urls()

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
            history = Record.objects.filter(mentee_name_id__in=[source.pk, target.pk])
            if province_id is None or history.exclude(
                session__skill_lab__facility__districtfk__provincefk_id=province_id
            ).exists():
                raise PermissionDenied('A national administrator must review this history.')
        return source, target

    def _preview(self, source, target, lock=False):
        queryset = Record._base_manager.filter(mentee_name_id__in=[source.pk,target.pk]).order_by('pk')
        if lock: queryset = queryset.select_for_update()
        rows = list(queryset)
        identities=[(r.mentee_name_id,r.session_id,r.topic_id) for r in rows]
        if len(identities)!=len(set(identities)):
            raise ValidationError('Multiple participant rows exist for one mentee, session and topic. Ask the administrator to reconcile these records first.')
        target_keys = {(r.session_id,r.topic_id):r for r in rows if r.mentee_name_id==target.pk}
        conflicts=[]
        for row in rows:
            existing=target_keys.get((row.session_id,row.topic_id))
            if row.mentee_name_id==source.pk and existing:
                conflicts.append({'source':row,'target':existing})
        inventory=related_inventory(source)
        # Session edits affect the meaning of a review and therefore invalidate it.
        session_model=Record._meta.get_field('session').remote_field.model
        sessions=session_model._base_manager.filter(pk__in={r.session_id for r in rows}).order_by('pk')
        if lock:sessions=sessions.select_for_update()
        payload={'source':snapshot(source),'target':snapshot(target),
                 'records':[snapshot(r) for r in rows], 'sessions':[snapshot(o) for o in sessions],
                 'inventory':inventory,'target_inventory':related_inventory(target)}
        digest=hashlib.sha256(json_text(payload).encode()).hexdigest()
        count=sum(r.mentee_name_id==source.pk for r in rows)
        return dict(source=source,target=target,details=rows,statuses=[],conflicts=conflicts,
            source_details=count,source_statuses=len({r.topic_id for r in rows if r.mentee_name_id==source.pk}),
            collision_count=len(conflicts),move_count=count-len(conflicts),inventory=inventory,
            has_history=bool(inventory),blocked=any(not x['supported'] for x in inventory),payload=payload,digest=digest)

    def _view_permissions(self, request):
        if not request.user.is_active or not request.user.is_staff or not self.has_view_permission(request):
            raise PermissionDenied
        opts=Record._meta
        if not request.user.has_perm(f'{opts.app_label}.view_{opts.model_name}'):
            raise PermissionDenied('Skill lab participant record view permission is required.')

    def _write_permissions(self, request, source, target, undo=False):
        permission='undo_merge' if undo else 'merge_mentees'
        if not request.user.has_perm('skilllab_review.'+permission):raise PermissionDenied
        if not all(self.has_change_permission(request,obj) for obj in (source,target)):raise PermissionDenied
        opts=Record._meta
        # Recreating and removing collision rows requires add and delete as well as change.
        for verb in ('add','change','delete'):
            if not request.user.has_perm(f'{opts.app_label}.{verb}_{opts.model_name}'):raise PermissionDenied

    def has_delete_permission(self, request, obj=None):
        # No ordinary admin deletion of archived Staff, including delete_selected.
        if obj is not None and ReviewMerge.objects.filter(active=True, source_id=obj.pk).exists():
            return False
        return super().has_delete_permission(request, obj)

    def _sign(self, request, state):
        return signing.dumps({**state, 'user': str(request.user.pk)}, salt='skilllab-review-wizard', compress=True)

    def _unsign(self, request):
        try:
            state = signing.loads(request.POST.get('state', ''), salt='skilllab-review-wizard', max_age=1800)
        except signing.BadSignature as exc:
            raise ValidationError('This review has expired. Choose the pair again to start a fresh review.') from exc
        if state.get('user') != str(request.user.pk):
            raise PermissionDenied
        if state.get('step') not in range(3, 8):
            raise ValidationError('Start from the facility selection.')
        return state

    def _different_statuses(self, preview):
        fields=[f for f in Record._meta.concrete_fields if not f.primary_key and f.name!='mentee_name'
                and not getattr(f,'auto_now',False) and not getattr(f,'auto_now_add',False)]
        return [c for c in preview['conflicts'] if any(
            getattr(c['source'],f.attname)!=getattr(c['target'],f.attname) for f in fields)]

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
        if not request.user.has_perm('skilllab_review.merge_mentees'):raise PermissionDenied
        if not state.get('same_person') or len(state.get('verification','').strip())<10:
            raise ValidationError('Confirm identity and describe how it was verified.')
        if not all(request.POST.get(k)=='yes' for k in ('confirm_identity','confirm_keep','confirm_history')):
            raise ValidationError('Check all three final confirmations.')
        with transaction.atomic():
            if ReviewMerge.objects.filter(active=True,source_id=state['source']).exists():
                raise ValidationError('This mentee is already archived. Check merge history.')
            preview=self._check_state(request,state,lock=True)
            source,target=preview['source'],preview['target']
            self._write_permissions(request,source,target)
            if ReviewMerge.objects.filter(active=True,source_id__in=[source.pk,target.pk]).exists():
                raise ValidationError('One of these mentees is archived. Start a fresh review.')
            if preview['blocked']:raise ValidationError('Other linked records need administrator review. No changes were applied.')
            if preview['collision_count'] and request.POST.get('confirm_collisions')!='yes':
                raise ValidationError('Confirm that one current row will remain for each overlapping session and topic, with both originals archived for undo.')
            choices=state.get('choices',{})
            differing={str(c['source'].pk) for c in self._different_statuses(preview)}
            if set(choices)!=differing or any(v not in {'source','target'} for v in choices.values()):
                raise ValidationError('Choose the complete record to retain for every differing session and topic.')
            before=json.loads(json_text(preview['payload']))
            collision_ids=set()
            for conflict in preview['conflicts']:
                old,existing=conflict['source'],conflict['target']
                collision_ids.add(old.pk)
                if choices.get(str(old.pk),'target')=='source':
                    for f in Record._meta.concrete_fields:
                        if not f.primary_key and f.name!='mentee_name':
                            setattr(existing,f.attname,getattr(old,f.attname))
                    existing.full_clean()
                    Record._base_manager.filter(pk=existing.pk).update(**{
                        f.attname:getattr(existing,f.attname) for f in Record._meta.concrete_fields
                        if not f.primary_key and f.name!='mentee_name'})
                empty_delete_check(old)
                old.delete()
            for row in preview['details']:
                if row.pk is not None and row.mentee_name_id==source.pk and row.pk not in collision_ids:
                    row.mentee_name_id=target.pk
                    row.full_clean()
                    Record._base_manager.filter(pk=row.pk).update(mentee_name_id=target.pk)
            if related_inventory(source):raise ValidationError('Linked records remain. Nothing was committed.')
            Staff._base_manager.filter(pk=source.pk).update(status=False)
            source.refresh_from_db();target.refresh_from_db()
            after=self._preview(source,target,lock=True)
            expected={row[Record._meta.pk.attname]:dict(row) for row in before['records']}
            for conflict in preview['conflicts']:
                # Deleted source instances have pk=None; identify originals by the target key.
                original=next(row for row in before['records'] if row['mentee_name_id']==source.pk
                              and row['session_id']==conflict['target'].session_id and row['topic_id']==conflict['target'].topic_id)
                old_id=original[Record._meta.pk.attname];target_id=conflict['target'].pk
                if choices.get(str(old_id),'target')=='source':
                    expected[target_id]={**original,Record._meta.pk.attname:target_id,'mentee_name_id':target.pk}
                expected.pop(old_id)
            for row in expected.values():
                if row['mentee_name_id']==source.pk:row['mentee_name_id']=target.pk
            if json_text(after['payload']['sessions'])!=json_text(before['sessions']):
                raise ValidationError('A custom signal changed session information during transfer. Nothing was committed; ask the administrator to review the integration.')
            if json_text(after['payload']['records'])!=json_text([expected[k] for k in sorted(expected)]):
                raise ValidationError('Participant record verification failed. All changes were rolled back.')
            record=ReviewMerge.objects.create(source_id=source.pk,target_id=target.pk,facility_id=source.hfname_id,
                actor_id=request.user.pk,actor_name=request.user.get_username(),verification=state['verification'],
                before=before,after_digest=after['digest'],choices=choices)
            self._audit(request,target,f'Skill lab merge {record.pk}: transferred history from mentee {source.pk}; duplicate archived; {len(collision_ids)} overlapping session/topic rows consolidated. Original snapshots retained for guarded undo.')
            self._audit(request,source,f'Skill lab merge {record.pk}: archived duplicate of mentee {target.pk}.')
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
            history = Record.objects.filter(mentee_name_id__in=pair)
            if history.exclude(session__skill_lab__facility__districtfk__provincefk_id=province_id).exists():
                raise PermissionDenied('A national administrator must review this history.')
        return source, target

    def _undo_merge(self, request, merge_id):
        if not request.user.has_perm('skilllab_review.undo_merge'):raise PermissionDenied
        with transaction.atomic():
            record=ReviewMerge.objects.get(pk=merge_id)
            source,target=self._undo_pair(request,record,lock=True)
            record=ReviewMerge.objects.select_for_update().get(pk=merge_id)
            self._write_permissions(request,source,target,undo=True)
            if not record.active:raise ValidationError('This merge has already been undone.')
            overlap=Q(source_id__in=[source.pk,target.pk])|Q(target_id__in=[source.pk,target.pk])
            if ReviewMerge.objects.filter(overlap,active=True,pk__gt=record.pk).exists():
                raise ValidationError('Undo the newer merge involving these mentees first.')
            current=self._preview(source,target,lock=True)
            if current['digest']!=record.after_digest:
                raise ValidationError('Mentee, participant or session records changed after the merge. Automatic undo is blocked to protect later work. Ask the administrator to reconcile the history.')
            originals=record.before['records'];current_ids={r.pk for r in current['details']}
            pk_name=Record._meta.pk.attname
            missing_ids={row[pk_name] for row in originals if row[pk_name] not in current_ids}
            if Record._base_manager.filter(pk__in=missing_ids).exists():
                raise ValidationError('An original participant record ID is now in use. Undo is blocked.')
            def values(row):
                return {f.attname:f.to_python(row[f.attname]) for f in Record._meta.concrete_fields}
            # Move original source rows back first to release the session/mentee/topic keys.
            for row in originals:
                if row[pk_name] in current_ids and row['mentee_name_id']==source.pk:
                    Record._base_manager.filter(pk=row[pk_name]).update(mentee_name_id=source.pk)
            for row in originals:
                data=values(row);pk=data.pop(pk_name)
                if pk in current_ids:Record._base_manager.filter(pk=pk).update(**data)
            Record._base_manager.bulk_create([Record(**values(row)) for row in originals if row[pk_name] in missing_ids])
            # Preserve date fields exactly even if a future model adds automatic timestamps.
            for row in originals:
                if row[pk_name] in missing_ids:
                    data=values(row);pk=data.pop(pk_name)
                    Record._base_manager.filter(pk=pk).update(**data)
            Staff._base_manager.filter(pk=source.pk).update(status=record.before['source']['status'])
            source.refresh_from_db();target.refresh_from_db()
            if json_text(self._preview(source,target,lock=True)['payload'])!=json_text(record.before):
                raise ValidationError('Restoration verification failed. All undo changes were rolled back.')
            record.active=False;record.undone_at=timezone.now();record.undone_by=request.user.pk
            record.save(update_fields=['active','undone_at','undone_by'])
            self._audit(request,target,f'Skill lab merge {record.pk} undone. Original participant rows and mentee links restored.')
            self._audit(request,source,f'Skill lab merge {record.pk} undone. Original active state restored.')
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
        topic=left.topic
        label=(getattr(topic,'nameeng',None) or getattr(topic,'namedari',None) or topic.name)
        title=f'{label} — {left.session.session_date} — Session {left.session_id}'
        rows=[]
        for f in left._meta.concrete_fields:
            if f.primary_key or f.name in {'mentee_name','session','topic'}:continue
            if getattr(f,'auto_now',False) or getattr(f,'auto_now_add',False):continue
            def show(obj):
                display=getattr(obj,'get_'+f.name+'_display',None)
                value=display() if display else getattr(obj,f.name)
                if isinstance(value,bool):return 'Yes' if value else 'No'
                return str(value) if value is not None and value!='' else 'Not recorded'
            labels={'ls':'Learning session recorded','mc':'Model competency recorded','thematic_area':'Thematic area',
                'competency_status':'Competency status','pre_test_score':'Pre test score','post_test_score':'Post test score',
                'demonstration_done':'Demonstration done','return_demonstration_done':'Return demonstration done',
                'checklist_score':'Checklist score','feedback_given':'Feedback given','next_followup_date':'Next follow up date',
                'remarks':'Remarks'}
            rows.append({'label':labels.get(f.name,str(f.verbose_name).replace('_',' ').capitalize()),'a':show(left),'b':show(right)})
        return {'id':str(left.pk),'topic':title,'rows':rows}

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
                                    decision='unsure',note='Overlapping session/topic participant records need mentor verification. '+state.get('verification',''),actor_id=request.user.pk)
                                state=None
                            elif remaining and choice in {'source','target'}:
                                state['choices'][str(remaining[0]['source'].pk)]=choice
                                if len(state['choices'])==len(conflicts):state['step']=7
                            else:raise ValidationError('Choose the complete participant record to retain, or select I need help.')
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
            detail_counts=dict(Record.objects.filter(mentee_name_id__in=ids).values_list('mentee_name_id').annotate(n=Count('pk')))
            status_counts=dict(Record.objects.filter(mentee_name_id__in=ids).values_list('mentee_name_id').annotate(n=Count('topic_id',distinct=True)))
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
        context={**self.admin_site.each_context(request),'opts':self.model._meta,'title':'Guided skill lab duplicate review',
                 'step':step,'facilities':facilities,'selected':selected,'roster':roster,'candidates':candidates,
                 'decisions':decisions,'review_error':error,'outcome':outcome,'result':result,
                 'can_merge':request.user.has_perm('skilllab_review.merge_mentees'),'home_url':self.duplicate_url(),'history_url':reverse(f'{self.admin_site.name}:skill_lab_skill_lab_mentee_merge_history')}
        if state and preview:
            a,b=preview['source'],preview['target']
            different=self._different_statuses(preview)
            remaining=[c for c in different if str(c['source'].pk) not in state['choices']]
            summaries=[]
            for conflict in different:
                use_source=state['choices'].get(str(conflict['source'].pk))=='source'
                chosen=conflict['source'] if use_source else conflict['target']
                progress=chosen.get_competency_status_display()
                progress={'IN_PROGRESS':'Learning in progress','COMPETENT':'Competent'}.get(str(progress),str(progress))
                summaries.append({'topic':self._status_card(conflict)['topic'],'choice':progress+' — '+('use complete participant values from the mentee being archived' if use_source else 'keep complete existing participant values of the retained mentee')})
            context.update(state_token=self._sign(request,state),preview=preview,identity_rows=self._identity_rows(a,b),
                topic_card=self._status_card(remaining[0]) if remaining else None,topic_number=len(state['choices'])+1,
                topic_total=len(different),identical_topics=len(preview['conflicts'])-len(different),
                status_summaries=summaries,verification=state.get('verification',''))
        return TemplateResponse(request,'admin/skill_lab/skill_lab_mentee/duplicates.html',context)

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
            if not request.user.has_perm('skilllab_review.undo_merge'):raise PermissionDenied
        return TemplateResponse(request,'admin/skill_lab/skill_lab_mentee/merge_history.html',{
            **self.admin_site.each_context(request),'opts':self.model._meta,'title':'Skill lab merge history',
            'records':visible,'confirm':confirm,'review_error':error,'notice':notice,
            'can_undo':request.user.has_perm('skilllab_review.undo_merge'),'home_url':self.duplicate_url()})

    def get_queryset(self, request):
        qs=super().get_queryset(request).exclude(pk__in=archived_ids())
        if request.GET.get('_popup') == '1' or (
            request.GET.get('app_label') == 'skill_lab' and
            request.GET.get('model_name') == Record._meta.model_name and
            request.GET.get('field_name') == 'mentee_name'
        ):
            qs=qs.filter(status=True)
        if request.user.is_superuser:return qs
        from hiva.admin_utils import user_province
        province=user_province(request);pid=getattr(province,'id',province)
        return qs.filter(hfname__districtfk__provincefk_id=pid) if pid is not None else qs.none()

    def changelist_view(self, request, extra_context=None):
        extra_context={**(extra_context or {}),
            'review_parent_template':getattr(self,'_skilllab_review_parent_template',None) or 'admin/change_list.html'}
        return super().changelist_view(request,extra_context=extra_context)


class _ArchivedChoiceMixin:
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field=super().formfield_for_foreignkey(db_field,request,**kwargs)
        if db_field.remote_field.model is Staff and field is not None and field.queryset is not None:
            field.queryset=field.queryset.filter(status=True).exclude(pk__in=archived_ids())
            if not request.user.is_superuser:
                from hiva.admin_utils import user_province
                province=user_province(request);pid=getattr(province,'id',province)
                field.queryset=field.queryset.filter(hfname__districtfk__provincefk_id=pid) if pid is not None else field.queryset.none()
        return field


class _ActiveParticipantFormMixin:
    def clean(self):
        data=super().clean()
        # Check the original record too: changing its mentee must not bypass
        # the restriction on editing an inactive mentee's history.
        original_id=self.instance.pk or getattr(data.get('id'), 'pk', None)
        if original_id and Record._base_manager.filter(pk=original_id).exclude(
            mentee_name__status=True
        ).exists():
            raise ValidationError(
                'This record belongs to an inactive mentee and cannot be edited here. '
                'Please contact your administrator.'
            )
        return data


class _ActiveParticipantMixin:
    def get_queryset(self, request):
        return super().get_queryset(request).filter(
            mentee_name__status=True
        ).exclude(mentee_name_id__in=archived_ids())


class _ActiveParticipantAdminMixin(_ActiveParticipantMixin):
    def get_form(self, request, obj=None, **kwargs):
        form=super().get_form(request, obj, **kwargs)
        return type('ActiveParticipantForm', (_ActiveParticipantFormMixin, form), {})


class _ActiveParticipantInlineMixin(_ActiveParticipantMixin):
    def get_formset(self, request, obj=None, **kwargs):
        formset=super().get_formset(request, obj, **kwargs)
        form=type('ActiveParticipantInlineForm', (_ActiveParticipantFormMixin, formset.form), {})
        return type('ActiveParticipantFormSet', (formset,), {'form': form})


def install_skilllab_duplicate_review(admin_site):
    """Call once, at the END of skill_lab/admin.py after existing registrations.

    Preserves existing ModelAdmin methods, forms, filters, media and actions. Does
    not import or alter the mentorship app or its review tables.
    """
    from django.contrib import admin
    existing=admin_site._registry.get(Staff)
    if existing is None:
        class DefaultMenteeAdmin(admin.ModelAdmin):
            list_display=('id','firstname','lastname','fathername','hfname','position','status')
            search_fields=('firstname','lastname','fathername','tazkiranumber')
        admin_site.register(Staff,DefaultMenteeAdmin)
        existing=admin_site._registry[Staff]
    if getattr(existing,'_skilllab_review_installed',False):return
    parent=existing.change_list_template
    existing.__class__=type('GuidedSkillLabMenteeAdmin',(SkillLabDuplicateMenteeAdminMixin,existing.__class__),{})
    existing.change_list_template='admin/skill_lab/skill_lab_mentee/change_list_review.html'
    existing._skilllab_review_parent_template=parent
    existing._skilllab_review_installed=True
    # Apply active choices after existing province and facility filters.
    for model,model_admin in list(admin_site._registry.items()):
        if model._meta.app_label!='skill_lab':continue
        if not isinstance(model_admin,_ArchivedChoiceMixin):
            model_admin.__class__=type('ArchiveChoices'+model_admin.__class__.__name__,(_ArchivedChoiceMixin,model_admin.__class__),{})
        model_admin.inlines=tuple(type('ArchiveChoices'+inline.__name__,(_ArchivedChoiceMixin,inline),{})
            if not issubclass(inline,_ArchivedChoiceMixin) else inline for inline in model_admin.inlines)

        if model is Record and not isinstance(model_admin, _ActiveParticipantAdminMixin):
            model_admin.__class__=type(
                'ActiveParticipants'+model_admin.__class__.__name__,
                (_ActiveParticipantAdminMixin, model_admin.__class__), {}
            )
        model_admin.inlines=tuple(
            type('ActiveParticipants'+inline.__name__, (_ActiveParticipantInlineMixin, inline), {})
            if inline.model is Record and not issubclass(inline, _ActiveParticipantInlineMixin)
            else inline for inline in model_admin.inlines
        )

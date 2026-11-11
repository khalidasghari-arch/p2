"""Read-only comparisons. Registration matches never imply clinical competency."""
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.utils.dateparse import parse_date
from .models import MenteeMatch


def norm(value):
    return re.sub(r'\s+', ' ', str(value or '').strip()).casefold()


def source_models():
    staff = apps.get_model('mentorship', 'Staff')
    skill = MenteeMatch._meta.get_field('skill_mentee').remote_field.model
    app = skill._meta.app_label
    return staff, skill, apps.get_model('mentorship', 'Mentorshipdetails'), apps.get_model(app, 'SkillLabParticipantRecord')


def province_id(request):
    if request.user.is_superuser:
        return None
    value = None
    try:
        from hiva.admin_utils import user_province
        value = user_province(request)
    except ImportError:
        pass
    if not value:
        for owner in [request.user]:
            value = getattr(owner, 'province_id', None) or getattr(owner, 'province', None)
    if not value:
        try:
            profile = request.user.profile
            value = getattr(profile, 'province_id', None) or getattr(profile, 'province', None)
        except (AttributeError, ObjectDoesNotExist):
            pass
    value = getattr(value, 'pk', value)
    if not value:
        raise PermissionDenied('Your account needs a province assignment to view this dashboard.')
    return value


def permitted(user):
    if not user.is_active or not user.is_staff:
        return False
    _, skill, _, record = source_models()
    return user.is_superuser or all(user.has_perm(p) for p in [
        'mentee_comparison.view_menteematch', 'mentorship.view_staff',
        'mentorship.view_mentorshipdetails',
        f'{skill._meta.app_label}.view_{skill._meta.model_name}',
        f'{record._meta.app_label}.view_{record._meta.model_name}',
    ])


def scoped_people(request):
    staff, skill, _, _ = source_models()
    pid = province_id(request)
    q1 = staff.objects.select_related('hfname__districtfk__provincefk', 'position')
    q2 = skill.objects.select_related('hfname__districtfk__provincefk', 'position')
    if pid is not None:
        q1 = q1.filter(hfname__districtfk__provincefk_id=pid)
        q2 = q2.filter(hfname__districtfk__provincefk_id=pid)
    return q1, q2, pid


def candidate_reason(s, k):
    if s.hfname_id != k.hfname_id:
        return None
    st, kt = norm(s.tazkiranumber), norm(k.tazkiranumber)
    first = norm(s.firstname)
    full = norm(f'{s.firstname} {s.lastname or ""}')
    other = norm(f'{k.firstname} {k.lastname or ""}')
    if st and kt and st == kt:
        return 'Same Tazkira; verify profile details'
    similar = first and (first == norm(k.firstname) or SequenceMatcher(None, full, other).ratio() >= .80)
    if not similar:
        return None
    if st and kt and st != kt:
        return 'Similar name, but conflicting Tazkira — investigate'
    exact = (full == other and norm(s.fathername) and norm(s.fathername) == norm(k.fathername)
             and s.position_id == k.position_id and s.gender == k.gender)
    return 'Exact profile suggestion — confirmation required' if exact else 'Similar name — confirmation required'


def date_filters(params):
    result = {}
    for key in ('start', 'end'):
        raw = params.get(key, '')
        try:
            value = parse_date(raw) if raw else None
        except ValueError:
            value = None
        if raw and not value:
            raise ValidationError('Enter valid dates in YYYY-MM-DD format.')
        result[key] = value
    if result['start'] and result['end'] and result['start'] > result['end']:
        raise ValidationError('The start date must be on or before the end date.')
    return result


def build_rows(request):
    q1, q2, pid = scoped_people(request)
    all_s, all_k = list(q1.order_by('firstname', 'id')), list(q2.order_by('firstname', 'id'))
    smap, kmap = {s.pk:s for s in all_s}, {k.pk:k for k in all_k}
    links = {m.staff_id:m for m in MenteeMatch.objects.filter(staff_id__in=smap, skill_mentee_id__in=kmap)}
    used = {m.skill_mentee_id for m in links.values()}
    by_facility = defaultdict(list)
    for k in all_k:
        by_facility[k.hfname_id].append(k)
    rows = []
    for s in all_s:
        link = links.get(s.pk)
        k = kmap.get(link.skill_mentee_id) if link else None
        valid = k is not None and s.hfname_id == k.hfname_id
        candidates = []
        if not valid:
            for possible in by_facility[s.hfname_id]:
                reason = candidate_reason(s, possible)
                if reason:
                    candidates.append({'person':possible, 'reason':reason, 'linked':possible.pk in used})
        state = 'confirmed' if valid else ('review' if candidates or link else 'mentorship_only')
        rows.append({'s':s, 'k':k, 'link':link, 'candidates':candidates,
                     'state':state, 'person':s, 'key':f'm-{s.pk}'})
    for k in all_k:
        if k.pk not in used:
            rows.append({'s':None, 'k':k, 'link':None, 'candidates':[],
                         'state':'skill_only', 'person':k, 'key':f'k-{k.pk}'})
    options_people = all_s + all_k
    provinces = {p.hfname.districtfk.provincefk_id:p.hfname.districtfk.provincefk.name for p in options_people}
    selected_province = request.GET.get('province', '')
    facilities = {p.hfname_id:p.hfname.name for p in options_people
                  if not selected_province or str(p.hfname.districtfk.provincefk_id) == selected_province}
    positions = {p.position_id:p.position.name for p in options_people}
    filtered = []
    for row in rows:
        p = row['person']
        pairs = [('province', p.hfname.districtfk.provincefk_id), ('facility',p.hfname_id), ('position',p.position_id)]
        if any(request.GET.get(key) and str(value) != request.GET[key] for key,value in pairs):
            continue
        gender = request.GET.get('gender', '')
        if gender and {'female':True,'male':False,'unknown':None}.get(gender) != p.gender:
            continue
        status = request.GET.get('active', '')
        if status and {'active':True,'inactive':False,'unknown':None}.get(status) != p.status:
            continue
        query = norm(request.GET.get('q', ''))
        if query and not any(query in norm(' '.join(str(v or '') for v in [x.pk, x.firstname,x.lastname,x.fathername])) for x in (row['s'],row['k']) if x):
            continue
        filtered.append(row)
    counts = Counter(r['state'] for r in filtered)
    state = request.GET.get('state', 'confirmed')
    shown = [r for r in filtered if not state or state == 'all' or r['state'] == state]
    return shown, counts, {'provinces':sorted(provinces.items(), key=lambda x:x[1]),
                          'facilities':sorted(facilities.items(), key=lambda x:x[1]),
                          'positions':sorted(positions.items(), key=lambda x:x[1])}, pid


def area_key(area):
    return ('hqip', area.hqip_area_id) if area.hqip_area_id else ('name', norm(area.name))


def session_timing(visit, side):
    start_field, end_field = (
        ('mentorshipstarttime', 'mentorshipendtime') if side == 'M'
        else ('check_in', 'check_out')
    )
    start = getattr(visit, start_field, None)
    end = getattr(visit, end_field, None)
    result = {'start_time': start, 'end_time': end,
              'duration_minutes': None, 'duration': 'Not recorded'}
    if start is None or end is None:
        return result
    seconds = lambda value: value.hour * 3600 + value.minute * 60 + value.second
    elapsed = seconds(end) - seconds(start)
    if elapsed < 0:
        result['duration'] = 'Check times: end is before start'
        return result
    minutes = elapsed // 60
    result.update(duration_minutes=minutes,
                  duration=f'{minutes // 60} h {minutes % 60:02d} min')
    return result


def enrich(rows, params, pid, evidence_url=None):
    dates = date_filters(params)
    _, skill, details, records = source_models()
    m_topics = list(apps.get_model('mentorship','MentorshipTopics').objects.select_related('thematicfk'))
    k_topics = list(apps.get_model(skill._meta.app_label,'SkillLabTopic').objects.select_related('thematicfk'))
    indexes = []
    for topics in (m_topics, k_topics):
        index = defaultdict(list)
        for t in topics:
            if t.thematicfk and norm(t.name):
                index[(area_key(t.thematicfk),norm(t.name))].append(t.pk)
        indexes.append(index)
    mappings = {}
    for side, topics in [('M',m_topics),('K',k_topics)]:
        for t in topics:
            key = (area_key(t.thematicfk), norm(t.name)) if t.thematicfk else None
            aligned = key and len(indexes[0].get(key,[])) == len(indexes[1].get(key,[])) == 1
            mappings[(side,t.pk)] = ('aligned',key) if aligned else (side,t.pk)
    confirmed = [r for r in rows if r['state']=='confirmed']
    mq = details.objects.filter(menteename_id__in=[r['s'].pk for r in confirmed]).select_related(
        'topicname__thematicfk','thematicname','mentorshipvistfk__facilityfk','mentor')
    kq = records.objects.filter(mentee_name_id__in=[r['k'].pk for r in confirmed]).select_related(
        'topic__thematicfk','thematic_area','session__skill_lab__facility','session__mentor_name')
    if pid is not None:
        mq = mq.filter(mentorshipvistfk__facilityfk__districtfk__provincefk_id=pid)
        kq = kq.filter(session__skill_lab__facility__districtfk__provincefk_id=pid)
    for field, lookup in [('start','gte'),('end','lte')]:
        if dates[field]:
            mq = mq.filter(**{f'mentorshipvistfk__visitdate__{lookup}':dates[field]})
            kq = kq.filter(**{f'session__session_date__{lookup}':dates[field]})
    grouped = defaultdict(list)
    for side, qs in [('M',mq),('K',kq)]:
        for obj in qs:
            mentee_id = obj.menteename_id if side=='M' else obj.mentee_name_id
            grouped[(side,mentee_id)].append(obj)
    for row in rows:
        row['topics'], row['areas'], row['sessions'] = [], [], []
        if row['state'] != 'confirmed':
            continue
        table = {}
        for side, person in [('M',row['s']),('K',row['k'])]:
            for obj in grouped[(side,person.pk)]:
                topic = obj.topicname if side=='M' else obj.topic
                recorded_area = obj.thematicname if side=='M' else obj.thematic_area
                area = topic.thematicfk if topic and topic.thematicfk else recorded_area
                mismatch = bool(topic and recorded_area and topic.thematicfk_id != recorded_area.pk)
                key = mappings.get((side,topic.pk), (side,'missing')) if topic else (side,'missing',getattr(area,'pk',None))
                if mismatch:
                    key = (side,'area-conflict', obj.pk)
                aligned = key[0]=='aligned'
                target = table.setdefault(key, {'area':str(area or 'Area not recorded'),
                    'topic':str(topic or 'Topic not recorded'), 'definition':getattr(topic,'nameeng','') or '',
                    'mapping':'Aligned by area + topic code' if aligned else ('Area conflict — review' if mismatch else 'Unmapped / source only'),
                    'm_ls':0,'m_pc':0,'m_mc':0,'k_ls':0,'k_mc':0,'m_n':0,'k_n':0,
                    'm_first':None,'m_last':None,'k_first':None,'k_last':None,'sessions':[]})
                prefix = side.lower()
                target[prefix+'_n'] += 1
                flags = ['ls','pc','mc'] if side=='M' else ['ls','mc']
                selected = [flag.upper() for flag in flags if getattr(obj,flag)]
                for flag in flags:
                    target[prefix+'_'+flag] += int(bool(getattr(obj,flag)))
                visit = obj.mentorshipvistfk if side=='M' else obj.session
                dt = (visit.visitdate if side=='M' else visit.session_date) if visit else None
                mentor = (obj.mentor if side=='M' else visit.mentor_name) if visit else (obj.mentor if side=='M' else None)
                facility = (visit.facilityfk if side=='M' else visit.skill_lab.facility) if visit else None
                if dt:
                    target[prefix+'_first'] = min(target[prefix+'_first'] or dt,dt)
                    target[prefix+'_last'] = max(target[prefix+'_last'] or dt,dt)
                event = {'source':'Mentorship' if side=='M' else 'Skill Lab', 'id':obj.pk,
                    'date':dt,'facility':str(facility or 'Not recorded'),'mentor':str(mentor or 'Not recorded'),
                    'type':', '.join(selected) or 'No LS/PC/MC selected',
                    'quality':'Multiple session flags — review' if len(selected)>1 else '',
                    'area':target['area'],'topic':target['topic'],
                    'evidence_url': evidence_url(obj, visit) if evidence_url else '',
                    'visit_id': visit.pk if visit else None}
                event.update(session_timing(visit, side))
                target['sessions'].append(event)
                row['sessions'].append(event)
        areas = {}
        for target in table.values():
            target['coverage'] = 'Both sources' if target['m_n'] and target['k_n'] else ('Mentorship only' if target['m_n'] else 'Skill Lab only')
            target['sessions'].sort(key=lambda e:(str(e['date'] or ''),e['source'],e['id']))
            a = areas.setdefault(target['area'], {'name':target['area'], **{k:0 for k in ['m_ls','m_pc','m_mc','k_ls','k_mc']}})
            for k in ['m_ls','m_pc','m_mc','k_ls','k_mc']:
                a[k] += target[k]
        row['topics'] = sorted(table.values(),key=lambda t:(t['area'],t['topic']))
        row['areas'] = sorted(areas.values(),key=lambda a:a['name'])
    return rows

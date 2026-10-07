from collections import Counter, defaultdict
from statistics import mean, median
from django.conf import settings
from django.db.models import Count, F, Q
from .models import MenteeTopicStatus, MentorshipTopics, Staff

def summarize_learning_history(events, selected_pairs, filters, status_map=None):
    """Count distinct LS visits before first dated PC/MC, per mentee/topic.

    Same-day LS/competency chronology is unknown from dates alone. Such pairs,
    and pairs with undated records, are reported but excluded from statistics.
    Duplicate detail lines in one visit count as one learning session.
    """
    status_map = status_map or {}
    groups = defaultdict(list)
    for event in events:
        pair = (event['mentee_id'], event['topic_id'])
        if pair in selected_pairs:
            groups[pair].append(event)
    results = []
    for pair, history in groups.items():
        successful = [e for e in history if e['date'] and (e['pc'] or e['mc'])]
        first_date = min((e['date'] for e in successful), default=None)
        if first_date:
            date_text = first_date.isoformat()
            if filters.get('date_from') and date_text < filters['date_from']:
                continue
            if filters.get('date_to') and date_text > filters['date_to']:
                continue
            # Require the first achievement to match activity filters too.
            # This prevents a later reassessment being called first competency.
            first = [e for e in successful if e['date'] == first_date]
            if not any(
                (not filters.get('mentor') or str(e['mentor_id']) == filters['mentor'])
                and (not filters.get('facility') or str(e['facility_id']) == filters['facility'])
                and (not filters.get('province') or str(e['province_id']) == filters['province'])
                and (not filters.get('thematic') or str(e['thematic_id']) == filters['thematic'])
                and (not filters.get('visit_round') or str(e['visit_round']) == filters['visit_round'])
                for e in first
            ):
                continue
        recorded_status = status_map.get(pair, {})
        stored_date = recorded_status.get('competent_date')
        earlier_status_date = bool(stored_date and first_date and stored_date < first_date)
        status_without_event = bool(recorded_status.get('status') == 'COMPETENT' and not first_date)
        missing_date = any(e['date'] is None for e in history)
        same_day = bool(first_date and any(e['ls'] and e['date'] == first_date for e in history))
        ls_visits = {
            e['visit_id'] for e in history
            if e['ls'] and e['date'] and (first_date is None or e['date'] < first_date)
        }
        if earlier_status_date:
            status = 'Stored competency predates PC/MC history — review required'
        elif status_without_event:
            status = 'Status says competent; dated PC/MC missing — review required'
        elif missing_date:
            status = 'Undated history — review required'
        elif same_day:
            status = 'Same-day sequence unknown — review required'
        elif first_date:
            status = 'First competency recorded'
        else:
            status = 'No dated competency recorded'
        results.append({
            'mentee_id': pair[0], 'topic_id': pair[1],
            'first_competency_date': first_date,
            'stored_competency_date': stored_date,
            'current_topic_status': {'NOT_STARTED': 'Not started', 'IN_PROGRESS': 'In progress', 'COMPETENT': 'Competent'}.get(recorded_status.get('status'), 'Not recorded'),
            'learning_sessions': len(ls_visits), 'status': status,
            'included': bool(first_date and not missing_date and not same_day and not earlier_status_date),
        })
    values = [r['learning_sessions'] for r in results if r['included']]
    return results, {
        'completed_pairs': len(values),
        'average_ls': round(mean(values), 2) if values else None,
        'median_ls': median(values) if values else None,
        'minimum_ls': min(values) if values else None,
        'maximum_ls': max(values) if values else None,
        'review_pairs': sum('review required' in r['status'] for r in results),
        'no_competency_pairs': sum(not r['first_competency_date'] for r in results),
    }, [{'sessions': n, 'pairs': count} for n, count in sorted(Counter(values).items())]


def build_dashboard_extensions(request, details_qs, scoped_history_qs, filters, province_id):
    """details_qs is already filtered; scoped_history_qs has authorization only."""
    if not request.user.is_superuser and province_id is None:
        details_qs = details_qs.none()
        scoped_history_qs = scoped_history_qs.none()

    # Current roster counts use province/facility. Activity selections additionally
    # restrict to unique mentees with a matching detail, avoiding join inflation.
    staff = Staff.objects.select_related('hfname__districtfk__provincefk')
    if not request.user.is_superuser:
        staff = staff.filter(hfname__districtfk__provincefk_id=province_id) if province_id is not None else staff.none()
    if filters.get('province'):
        staff = staff.filter(hfname__districtfk__provincefk_id=filters['province'])
    if filters.get('facility'):
        staff = staff.filter(hfname_id=filters['facility'])
    activity_selected = any(filters.get(k) for k in ('date_from', 'date_to', 'mentor', 'thematic', 'visit_round'))
    if activity_selected:
        staff = staff.filter(pk__in=details_qs.order_by().values('menteename_id'))
    counts = staff.aggregate(
        active=Count('pk', filter=Q(status=True)),
        inactive=Count('pk', filter=Q(status=False)),
        unspecified=Count('pk', filter=Q(status__isnull=True)),
        total=Count('pk'),
    )
    facility_status = list(staff.order_by().values(
        facility_id=F('hfname_id'), facility=F('hfname__name'),
        province=F('hfname__districtfk__provincefk__name'),
    ).annotate(
        active=Count('pk', filter=Q(status=True)),
        inactive=Count('pk', filter=Q(status=False)),
        unspecified=Count('pk', filter=Q(status__isnull=True)), total=Count('pk'),
    ).order_by('province', 'facility', 'facility_id'))
    roster_rows = list(staff.order_by('hfname__districtfk__provincefk__name', 'hfname__name', 'hfname_id', 'firstname', 'pk').values(
        'id', 'firstname', 'lastname', 'status', 'gender',
        facility_id=F('hfname_id'), facility=F('hfname__name'),
        province=F('hfname__districtfk__provincefk__name'), position_name=F('position__name'),
    ))
    for row in roster_rows:
        row['mentee'] = ' '.join(part for part in (row['firstname'], row['lastname']) if part)
        row['status_label'] = 'Active' if row['status'] is True else 'Inactive' if row['status'] is False else 'Unspecified'
        row['gender_label'] = 'Female' if row['gender'] is True else 'Male' if row['gender'] is False else 'Unspecified'

    def aggregate(qs):
        return qs.annotate(
            mentees=Count('menteename_id', distinct=True),
            visits=Count('mentorshipvistfk_id', distinct=True),
            records=Count('pk'), ls=Count('pk', filter=Q(ls=True)),
            pc=Count('pk', filter=Q(pc=True)), mc=Count('pk', filter=Q(mc=True)),
        )

    gender_rows = list(aggregate(details_qs.order_by().values('menteename__gender').exclude(
        menteename_id__isnull=True)).order_by('menteename__gender'))
    for row in gender_rows:
        value = row.pop('menteename__gender')
        row['gender'] = 'Female' if value is True else 'Male' if value is False else 'Unspecified'
    thematic_rows = list(aggregate(details_qs.order_by().exclude(thematicname_id__isnull=True).values(
        thematic_id=F('thematicname_id'), thematic=F('thematicname__name'),
    )).annotate(topics=Count('topicname_id', distinct=True)).order_by('thematic', 'thematic_id'))
    topic_rows = list(aggregate(details_qs.order_by().exclude(topicname_id__isnull=True).values(
        thematic_id=F('thematicname_id'), thematic=F('thematicname__name'),
        topic_id=F('topicname_id'), topic=F('topicname__name'),
    )).order_by('thematic', 'thematic_id', 'topic', 'topic_id'))
    definition_field = getattr(settings, 'MENTORSHIP_TOPIC_DEFINITION_FIELD', 'nameeng')
    MentorshipTopics._meta.get_field(definition_field)
    descriptions = {
        topic.pk: topic for topic in MentorshipTopics.objects.filter(
            pk__in=[r['topic_id'] for r in topic_rows])
    }
    for row in topic_rows:
        topic = descriptions[row['topic_id']]
        options = [(definition_field, getattr(topic, definition_field)), ('namedari', topic.namedari), ('namepashto', topic.namepashto)]
        field, text = next(((field, text) for field, text in options if text and str(text).strip()), ('', 'No topic description recorded'))
        row['definition'] = text
        row['definition_language'] = {'nameeng': 'English', 'namedari': 'Dari', 'namepashto': 'Pashto'}.get(field, 'Configured description') if field else ''
        row['thematic'] = row['thematic'] or 'Unassigned thematic area'

    pairs = set(details_qs.order_by().exclude(menteename_id__isnull=True).exclude(
        topicname_id__isnull=True).values_list('menteename_id', 'topicname_id'))
    # Entire authorized chronology, including sessions before the start filter.
    # Narrow by IDs in SQL and by exact selected pairs in the pure helper.
    history = scoped_history_qs.filter(
        menteename_id__in={p[0] for p in pairs}, topicname_id__in={p[1] for p in pairs},
    ).order_by().values(
        'ls', 'pc', 'mc', 'mentor_id',
        mentee_id=F('menteename_id'), topic_id=F('topicname_id'),
        date=F('mentorshipvistfk__visitdate'), visit_id=F('mentorshipvistfk_id'),
        province_id=F('mentorshipvistfk__facilityfk__districtfk__provincefk_id'),
        facility_id=F('mentorshipvistfk__facilityfk_id'),
        thematic_id=F('thematicname_id'), visit_round=F('mentorshipvistfk__visitround'),
    ).values('mentee_id', 'topic_id', 'date', 'visit_id', 'province_id',
             'facility_id', 'thematic_id', 'visit_round', 'ls', 'pc', 'mc', 'mentor_id')
    statuses = MenteeTopicStatus.objects.filter(
        mentee_id__in={p[0] for p in pairs}, topic_id__in={p[1] for p in pairs})
    if not request.user.is_superuser:
        statuses = statuses.filter(mentee__hfname__districtfk__provincefk_id=province_id) if province_id is not None else statuses.none()
    status_map = {(r['mentee_id'], r['topic_id']): r for r in statuses.values('mentee_id', 'topic_id', 'status', 'competent_date')}
    learning_rows, learning_stats, distribution = summarize_learning_history(history.iterator(chunk_size=2000), pairs, filters, status_map)
    names = {
        pk: ' '.join(part for part in (first, last) if part)
        for pk, first, last in Staff.objects.filter(pk__in={p[0] for p in pairs}).values_list('pk', 'firstname', 'lastname')
    }
    topics = dict(MentorshipTopics.objects.filter(pk__in={p[1] for p in pairs}).values_list('pk', 'name'))
    for row in learning_rows:
        row['mentee'] = names.get(row['mentee_id']) or str(row['mentee_id'])
        row['topic'] = topics.get(row['topic_id']) or str(row['topic_id'])
    learning_rows.sort(key=lambda r: (r['mentee'], r['topic'], r['mentee_id'], r['topic_id']))
    return {
        'mentee_status_kpis': counts, 'facility_status_rows': facility_status,
        'mentee_status_rows': roster_rows,
        'gender_rows': gender_rows, 'thematic_detail_rows': thematic_rows,
        'topic_detail_rows': topic_rows, 'learning_rows': learning_rows,
        'learning_stats': learning_stats, 'learning_distribution': distribution,
        'distinct_thematics_added': details_qs.exclude(thematicname_id__isnull=True).order_by().values('thematicname_id').distinct().count(),
        'distinct_topics_added': details_qs.exclude(topicname_id__isnull=True).order_by().values('topicname_id').distinct().count(),
        'mentee_status_scope_note': (
            'Current staff status; mentees with matching mentorship activity and a current facility matching the location filters.'
            if activity_selected else 'Current staff roster in the selected province/facility, including staff with no mentorship records.'
        ),
    }


def append_extension_sheets(workbook, data):
    """Call before the existing loop that styles every export sheet."""
    specifications = [
        ('Mentee_Status', 'facility_status_rows', [
            ('Province', 'province'), ('Facility ID', 'facility_id'), ('Facility', 'facility'),
            ('Active', 'active'), ('Inactive', 'inactive'), ('Unspecified', 'unspecified'), ('Total', 'total'),
        ]),
        ('Mentee_Roster', 'mentee_status_rows', [(key.title(), key) for key in ('province', 'facility_id', 'facility', 'id', 'mentee', 'position_name', 'gender_label', 'status_label')]),
        ('Gender', 'gender_rows', [(key.title(), key) for key in ('gender', 'mentees', 'visits', 'records', 'ls', 'pc', 'mc')]),
        ('Thematic_Detail', 'thematic_detail_rows', [(key.title(), key) for key in ('thematic_id', 'thematic', 'mentees', 'topics', 'visits', 'records', 'ls', 'pc', 'mc')]),
        ('Topic_Definitions', 'topic_detail_rows', [(key.title(), key) for key in ('thematic_id', 'thematic', 'topic_id', 'topic', 'definition', 'definition_language', 'mentees', 'visits', 'records', 'ls', 'pc', 'mc')]),
        ('Learning_To_Competency', 'learning_rows', [(key.title(), key) for key in ('mentee_id', 'mentee', 'topic_id', 'topic', 'learning_sessions', 'first_competency_date', 'stored_competency_date', 'current_topic_status', 'status', 'included')]),
        ('Learning_Distribution', 'learning_distribution', [('LS visits before first competency', 'sessions'), ('Mentee-topic pairs', 'pairs')]),
    ]
    for title, data_key, columns in specifications:
        sheet = workbook.create_sheet(title)
        sheet.append([label for label, key in columns])
        for row in data[data_key]:
            sheet.append([row.get(key) for label, key in columns])
        # Names/definitions are data, even when they begin with '='.
        for cells in sheet.iter_rows(min_row=2):
            for cell in cells:
                if isinstance(cell.value, str):
                    cell.data_type = 's'
    notes = workbook.create_sheet('Extension_Methodology')
    notes.append(['Measure', 'Explanation'])
    notes.append(['Current staff status', data['mentee_status_scope_note']])
    notes.append(['Competency unit', 'Mentee-topic pair, first dated Patient Competent or Model Competent.'])
    notes.append(['Stored competency date', 'MenteeTopicStatus.competent_date is displayed for comparison. It has no visit/mentor reference; it is not used to invent an achievement event. An earlier stored date or competent status without a dated PC/MC event triggers review and exclusion from summaries.'])
    notes.append(['LS count', 'Distinct visits for the same mentee/topic strictly before first competency; repeated detail rows in one visit count once.'])
    notes.append(['History and filters', 'All authorized history contributes to LS counts. Filters select first achievement events, not subsequent reassessments. Earlier history outside the user province cannot be used.'])
    notes.append(['Excluded from summaries', 'Pairs with undated history or same-day LS/competency. Zero LS means no earlier LS recorded.'])
    for key, value in data['learning_stats'].items():
        notes.append([key, value])

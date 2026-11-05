"""Read-only, permission-scoped source records behind an LS sequence finding."""
from urllib.parse import urlencode
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse
from django.template.response import TemplateResponse
from django.urls import reverse, NoReverseMatch
from .models import Mentorshipvisit, MentorshipTopics
from .dashboard_sequence import classify_sequence
from .dashboard_quality import display_name, MISSING_FATHER


def sequence_evidence_view(model_admin, request):
    if not model_admin.has_view_permission(request):
        raise PermissionDenied
    try:
        mid, tid, fid = [int(request.GET[k]) for k in ('review_mentee', 'review_topic', 'review_facility')]
    except (KeyError, TypeError, ValueError):
        raise Http404('Select a valid mentee and topic from the dashboard.')
    _, authorized = model_admin._base_querysets(request)
    visits, _ = model_admin._base_querysets(request)
    _, selected, filters = model_admin._apply_filters(request, visits, authorized)
    from django.db.models import Q
    selected = selected.filter(menteename_id=mid, topicname_id=tid,
                               mentorshipvistfk__facilityfk_id=fid).filter(Q(pc=True) | Q(mc=True))
    first_selected = selected.order_by('mentorshipvistfk__visitdate', 'pk').first()
    if first_selected is None:
        # Do not reveal names, existence or history for tampered or hidden IDs.
        raise Http404('No matching competency is available under your access and selected filters.')
    history = authorized.filter(menteename_id=mid, topicname_id=tid)
    if filters.get('date_to'):
        history = history.filter(Q(mentorshipvistfk__visitdate__lte=filters['date_to']) |
                                 Q(mentorshipvistfk__visitdate__isnull=True))
    selected_ids = set(selected.values_list('pk', flat=True))
    records = []
    visit_objects = {}
    for d in history.order_by('mentorshipvistfk__visitdate', 'pk'):
        v = d.mentorshipvistfk
        visit_objects[v.pk] = v
        records.append({'id': d.pk, 'date': v.visitdate, 'visit_id': v.pk,
            'facility_id': v.facilityfk_id, 'facility': str(v.facilityfk.name),
            'province': str(v.facilityfk.districtfk.provincefk.name),
            'mentor': str(d.mentor.name) if d.mentor else 'Mentor not entered',
            'ls': d.ls, 'pc': d.pc, 'mc': d.mc,
            'activity': ' + '.join(k for k, flag in [('LS', d.ls), ('PC', d.pc), ('MC', d.mc)] if flag) or 'No activity flag',
            'selected_competency': d.pk in selected_ids,
            'source_url': ''})
    check = classify_sequence(records, fid)
    counts = {key: sum(bool(r[key]) for r in records) for key in ('ls', 'pc', 'mc')}
    first_date = check['first_competency_date']
    for r in records:
        if not r['date']:
            r['sequence_note'] = 'Date missing'
        elif r['ls'] and first_date and r['date'] < first_date:
            r['sequence_note'] = 'LS before first recorded PC/MC'
        elif r['ls'] and first_date and r['date'] == first_date:
            r['sequence_note'] = 'LS on first PC/MC date; order unknown'
        elif r['ls'] and first_date and r['date'] > first_date:
            r['sequence_note'] = 'LS after first recorded PC/MC'
        elif (r['pc'] or r['mc']) and r['date'] == first_date:
            r['sequence_note'] = 'First recorded competency date'
        else:
            r['sequence_note'] = 'Later record' if first_date else 'No dated competency to compare'
    mentee = first_selected.menteename
    mentee_name = display_name(' '.join(p for p in [mentee.firstname, mentee.lastname] if p))
    father = display_name(mentee.fathername) or MISSING_FATHER
    topic = first_selected.topicname
    same_codes = list(MentorshipTopics.objects.filter(name=topic.name,
        thematicfk_id=topic.thematicfk_id).exclude(pk=tid).values('id', 'name'))
    clean_query = {k: v for k, v in filters.items() if v}
    back_url = '?' + urlencode(clean_query)
    export_query = dict(clean_query, sequence_evidence='1', review_mentee=mid,
                        review_topic=tid, review_facility=fid, sequence_export='1')
    if request.GET.get('sequence_export') == '1':
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
        wb = Workbook(); ws = wb.active; ws.title = 'Record_evidence'
        ws.append(['Mentee', mentee_name, 'Mentee ID', mid, 'Father name', father])
        ws.append(['Topic', topic.name, 'Topic ID', tid, 'Profile facility', first_selected.mentorshipvistfk.facilityfk.name])
        ws.append(['Evidence scope', 'Authorized history for this exact mentee/topic; all earlier dates and accessible facilities/mentors; end date: ' + (filters.get('date_to') or 'no upper limit')])
        ws.append(['Finding', check['interpretation'], 'LS records', counts['ls'], 'PC records', counts['pc'], 'MC records', counts['mc']])
        ws.append(['First PC/MC date', first_date, 'Prior distinct LS visits', check['prior_ls_visits']])
        ws.append(['Limit', 'Different mentee/topic IDs and inaccessible records are not searched; absence of a matched LS is not proof that learning never happened.'])
        ws.append([])
        ws.append(['Detail record ID', 'Date', 'Province', 'Facility', 'Mentor', 'LS', 'PC', 'MC', 'Selected competency', 'Sequence explanation', 'Visit ID reference'])
        for r in records:
            ws.append([r['id'], r['date'], r['province'], r['facility'], r['mentor'], int(r['ls']), int(r['pc']), int(r['mc']), 'Yes' if r['selected_competency'] else 'No', r['sequence_note'], r['visit_id']])
        for row in ws:
            for cell in row:
                if isinstance(cell.value, str): cell.data_type = 's'
                cell.alignment = Alignment(vertical='top', wrap_text=True)
        for cell in ws[8]:
            cell.font = Font(bold=True, color='FFFFFF'); cell.fill = PatternFill('solid', fgColor='083D33')
        for col, width in {'A':20,'B':18,'C':24,'D':36,'E':28,'F':12,'G':12,'H':12,'I':22,'J':48,'K':20}.items():
            ws.column_dimensions[col].width = width
        for row in ws.iter_rows(min_row=9): row[1].number_format = 'yyyy-mm-dd'
        ws.freeze_panes = 'C9'; ws.auto_filter.ref = f'A8:K{ws.max_row}'
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="Mentee_{mid}_Topic_{tid}_Evidence.xlsx"'
        wb.save(response)
        return response
    page = Paginator(records, 100).get_page(request.GET.get('evidence_page'))
    # Source forms retain their own normal Django permissions and validation.
    source_admin = model_admin.admin_site._registry.get(Mentorshipvisit)
    permission_cache = {}
    for r in page.object_list:
        v = visit_objects[r['visit_id']]
        if v.pk not in permission_cache:
            allowed = source_admin and source_admin.has_view_permission(request, v)
            try:
                permission_cache[v.pk] = reverse(f'{model_admin.admin_site.name}:mentorship_mentorshipvisit_change', args=[v.pk]) if allowed else ''
            except NoReverseMatch:
                permission_cache[v.pk] = ''
        r['source_url'] = permission_cache[v.pk]
    def page_url(number):
        query = request.GET.copy(); query['evidence_page'] = str(number)
        query.pop('sequence_export', None); query.pop('export', None)
        return '?' + query.urlencode()
    context = {**model_admin.admin_site.each_context(request), 'title': 'Mentorship record evidence',
        'mentee_name': mentee_name, 'fathername': father, 'mentee_id': mid,
        'topic': topic.name, 'topic_id': tid, 'same_codes': same_codes,
        'profile_facility': first_selected.mentorshipvistfk.facilityfk.name,
        'scope_end': filters.get('date_to') or 'No upper date limit', 'counts': counts,
        'selected_count': len(selected_ids), 'check': check, 'records_page': page,
        'back_url': back_url, 'evidence_export_url': '?' + urlencode(export_query),
        'previous_url': page_url(page.previous_page_number()) if page.has_previous() else '',
        'next_url': page_url(page.next_page_number()) if page.has_next() else ''}
    return TemplateResponse(request, 'admin/mentorship/dashboard_evidence.html', context)

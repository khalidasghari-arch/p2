"""HQIP comparisons using the existing dashboard's criterion/standard rollups."""
from collections import defaultdict
from datetime import date
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse


def progress_context(admin, request):
    if not admin.has_view_permission(request):
        raise PermissionDenied
    # Explicit fail-closed province check supplements the inherited admin mixin.
    allowed = admin.get_queryset(request)
    if not request.user.is_superuser:
        from .admin import user_province
        province = user_province(request)
        pid = getattr(province, 'pk', province)
        allowed = allowed.filter(facilityfk__districtfk__provincefk_id=pid) if pid else allowed.none()
    filters = {}
    errors = []
    for key in ('province', 'district', 'facility_type', 'facility', 'area', 'baseline', 'comparison'):
        value = request.GET.get(key, '').strip()
        filters[key] = value if value.isdigit() else ''
        if value and not value.isdigit():
            errors.append('Invalid filter value. Reset the filters and try again.')
    def options(qs, path):
        return [{'id':pk, 'name':name} for pk,name in qs.order_by(path+'__name',path+'__pk').values_list(path+'__pk',path+'__name').distinct()]
    provinces = options(allowed, 'facilityfk__districtfk__provincefk')
    headers = allowed
    for key,path in (('province','facilityfk__districtfk__provincefk_id'),('district','facilityfk__districtfk_id'),('facility_type','facilityfk__facilitytypefk_id'),('facility','facilityfk_id'),('area','areafk_id')):
        if key == 'district':
            districts = options(headers, 'facilityfk__districtfk')
        if key == 'facility_type':
            facility_types = options(headers, 'facilityfk__facilitytypefk')
        if key == 'facility':
            facilities = options(headers, 'facilityfk')
        if key == 'area':
            areas = options(headers, 'areafk')
        if filters[key]:
            headers = headers.filter(**{path:filters[key]})
    # Chronology is the earliest recorded assessment date, not a guessed round ID.
    rounds_by_id = {}
    for rid,name,day in headers.order_by('assessmentdate','assessmenttype_id').values_list('assessmenttype_id','assessmenttype__name','assessmentdate'):
        rounds_by_id.setdefault(rid, {'id':rid,'name':name,'first_date':day})
    rounds = list(rounds_by_id.values())
    requested = [] if request.GET.get('all_rounds') == '1' else request.GET.getlist('rounds')
    # Keep older two-round URLs working. With no selection, include future rounds automatically.
    if not requested and request.GET.get('all_rounds') != '1' and (filters['baseline'] or filters['comparison']):
        requested = [v for v in (filters['baseline'], filters['comparison']) if v]
        if len(requested)==2 and requested[0]==requested[1]:
            errors.append('Choose different assessment rounds.')
    if any(not value.isdigit() or int(value) not in rounds_by_id for value in requested):
        errors.append('A selected round is unavailable in this scope. Reset the round selection.')
    selected_ids = {int(value) for value in requested if value.isdigit()}
    selected_rounds = [r for r in rounds if not requested or r['id'] in selected_ids]
    for r in rounds:
        r['selected'] = r in selected_rounds
    baseline = selected_rounds[0] if selected_rounds else None
    comparison = selected_rounds[-1] if selected_rounds else None
    if not selected_rounds:
        errors.append('No assessment rounds with data are available in the selected scope.')
    filters['baseline'] = str(baseline['id']) if baseline else ''
    filters['comparison'] = str(comparison['id']) if comparison else ''
    groups = [{'key':'thematic','title':'Progress by thematic area','rows':[]},
              {'key':'province','title':'Progress by province','rows':[]},
              {'key':'facility_type','title':'Progress by facility type','rows':[]}]
    data = {'filters':filters, 'province_options':provinces,'district_options':districts,
            'type_options':facility_types,'facility_options':facilities,'area_options':areas,
            'round_options':rounds,'selected_rounds':selected_rounds,'selected_count':len(selected_rounds),
            'all_rounds_mode':not requested,'round_coverage':[], 'chart_payload':{'rounds':selected_rounds,'groups':[]},'baseline':baseline,'comparison':comparison,'errors':errors,
            'groups':groups,'baseline_score':None,'comparison_score':None,'gain':None,
            'matched_facilities':0,'matched_pairs':0,'excluded_baseline_pairs':0,'excluded_comparison_pairs':0,
            'baseline_headers':0,'comparison_headers':0,'duplicate_header_groups':0,
            'largest_gain':None,'highest_score':None,
            'methodology': 'Standard = YES / (YES + NO); section = mean of scored standards; thematic area = mean of scored sections; overall = mean of scored thematic areas. N/A and missing scores are excluded from the standard denominator. The existing dashboard scoring functions are reused; scores are not averaged from the slide.'}
    if errors:
        return data
    selected = headers.filter(assessmenttype_id__in=[r['id'] for r in selected_rounds])
    raw = admin._hqip_standard_rows(selected)
    meta = {fid:{'facility_type_id':tid,'facility_type':name or 'Unspecified'} for fid,tid,name in selected.values_list('facilityfk_id','facilityfk__facilitytypefk_id','facilityfk__facilitytypefk__name').distinct()}
    by_round = {r['id']:[] for r in selected_rounds}
    available = {rid:set() for rid in by_round}
    for row in raw:
        by_round[row['round_id']].append({**row,**meta[row['facility_id']]})
        if row['applicable']:
            available[row['round_id']].add((row['facility_id'],row['area_id']))
    matched = set.intersection(*available.values())
    observed = {rid:set(selected.filter(assessmenttype_id=rid).values_list('facilityfk_id','areafk_id')) for rid in by_round}
    data.update(matched_facilities=len({fid for fid,aid in matched}),matched_pairs=len(matched),
                excluded_baseline_pairs=len(observed[baseline['id']]-matched),excluded_comparison_pairs=len(observed[comparison['id']]-matched))
    for rid,key in ((baseline['id'],'baseline_headers'),(comparison['id'],'comparison_headers')):
        data[key] = selected.filter(assessmenttype_id=rid).count()
    from django.db.models import Count
    data['duplicate_header_groups'] = selected.values('facilityfk_id','areafk_id','assessmenttype_id').annotate(n=Count('pk')).filter(n__gt=1).count()
    if not matched:
        data['errors'].append('No facility–thematic pairs have applicable scores in every selected round. Select fewer rounds or adjust the filters.')
        return data
    kept = {rid:[r for r in rows if (r['facility_id'],r['area_id']) in matched] for rid,rows in by_round.items()}
    overall_values = []
    for r in selected_rounds:
        rid = r['id']
        value = admin._hqip_rollup_from_standard_rows(kept[rid])['overall_percent']
        overall_values.append(value)
        data['round_coverage'].append({**r,'score':value,'excluded_pairs':len(observed[rid]-matched),
                                       'matched_pairs':len(matched),'matched_facilities':data['matched_facilities']})
    data['baseline_score'], data['comparison_score'] = overall_values[0], overall_values[-1]
    data['gain'] = admin._hqip_change(data['comparison_score'],data['baseline_score']) if len(selected_rounds)>1 else None
    for group in groups:
        key = 'area' if group['key']=='thematic' else group['key']
        buckets = defaultdict(lambda:defaultdict(list))
        names = {}
        for rid,rows in kept.items():
            for row in rows:
                gid = row[key+'_id']
                buckets[gid][rid].append(row)
                names[gid] = row[key]
        for gid in sorted(buckets,key=lambda x:(names[x],x)):
            values = [admin._hqip_rollup_from_standard_rows(buckets[gid][r['id']])['overall_percent'] for r in selected_rounds]
            av,bv = values[0],values[-1]
            gain = admin._hqip_change(bv,av) if len(values)>1 else None
            group['rows'].append({'id':gid,'name':names[gid],'baseline':av,'comparison':bv,'gain':gain,
                                  'values':values,'baseline_width':str(av or 0),'comparison_width':str(bv or 0),
                                  'facilities':len({r['facility_id'] for r in buckets[gid][baseline['id']]}),
                                  'decline':gain is not None and gain<0})
    thematic = groups[0]['rows']
    data['largest_gain'] = max(thematic,key=lambda r:r['gain']) if thematic and len(selected_rounds)>1 else None
    data['highest_score'] = max(thematic,key=lambda r:r['comparison']) if thematic else None
    data['chart_payload'] = {'rounds':selected_rounds,'groups':groups,'overall':overall_values}
    return data


def export_progress(data):
    """Small summary-only workbook; avoid exporting every assessment detail."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    wb = Workbook()
    ws = wb.active
    ws.title = 'Summary'
    ws.append(['HQIP assessment progress','Value'])
    for label,value in [('Baseline round',data['baseline']['name'] if data['baseline'] else ''),('Comparison round',data['comparison']['name'] if data['comparison'] else ''),('Baseline score %',data['baseline_score']),('Comparison score %',data['comparison_score']),('Gain (percentage points)',data['gain']),('Matched facilities',data['matched_facilities']),('Matched facility-thematic pairs',data['matched_pairs']),('Excluded baseline pairs',data['excluded_baseline_pairs']),('Excluded comparison pairs',data['excluded_comparison_pairs']),('Repeated facility-area-round header groups',data['duplicate_header_groups']),('Scoring',data['methodology']),('Coverage','Only facility-thematic pairs with applicable scores in all selected rounds are compared. Underlying standards may differ. Repeated headers are pooled following the existing dashboard.'),('Source','MNHIMS')]:
        ws.append([label,value])
    ws.append(['Selected rounds', ' | '.join(r['name'] for r in data['selected_rounds'])])
    ws.append(['Round mode', 'All available rounds (includes new rounds)' if data['all_rounds_mode'] else 'Selected rounds only'])
    for r in data['round_coverage']:
        ws.append(['Coverage: '+r['name'], str(r['matched_pairs'])+' matched pairs; '+str(r['excluded_pairs'])+' excluded'])
    for key,value in data['filters'].items(): ws.append(['Filter: '+key,value or 'All'])
    for error in data['errors']: ws.append(['Notice',error])
    for group in data['groups']:
        sheet = wb.create_sheet({'thematic':'Thematic areas','province':'Provinces','facility_type':'Facility types'}[group['key']])
        sheet.append(['Group']+[r['name']+' (%)' for r in data['selected_rounds']]+['First-to-last gain (pp)','Matched facilities'])
        for r in group['rows']: sheet.append([r['name']]+r['values']+[r['gain'],r['facilities']])
    header_font=Font(name='Calibri',bold=True,color='FFFFFF'); body=Font(name='Calibri',size=11,color='173C35')
    green=PatternFill('solid',fgColor='083D33'); pale=PatternFill('solid',fgColor='F0F7F4')
    for sheet in wb:
        sheet.freeze_panes='B2';sheet.auto_filter.ref=sheet.dimensions;sheet.sheet_view.showGridLines=False
        for row in sheet:
            for cell in row:
                cell.font=header_font if cell.row==1 else body
                cell.alignment=Alignment(vertical='top',wrap_text=True)
                if cell.row==1: cell.fill=green
                elif cell.row%2==0: cell.fill=pale
                if isinstance(cell.value,str): cell.data_type='s'
                if isinstance(cell.value,float):cell.number_format='0.00'
        sheet.column_dimensions['A'].width=48
        from openpyxl.utils import get_column_letter
        for col in range(2,sheet.max_column+1):sheet.column_dimensions[get_column_letter(col)].width=23 if sheet.title!='Summary' else 70
    response=HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition']='attachment; filename="HQIP_Progress_'+date.today().isoformat()+'.xlsx"'
    wb.save(response)
    return response

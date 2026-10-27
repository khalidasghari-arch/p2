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
    for key in ('province', 'district', 'facility_type', 'facility', 'area', 'section', 'standard', 'criterion', 'baseline', 'comparison'):
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
    from .models import HQIPAssessment
    from django.db.models import F
    detail_options = {}
    for key,path in (('section','criteriafk__standardfk__sectionfk'),('standard','criteriafk__standardfk'),('criterion','criteriafk')):
        lines = HQIPAssessment.objects.filter(header__in=headers, criteriafk__standardfk__sectionfk__areafk_id=F('header__areafk_id'))
        if key != 'section' and filters['section']: lines = lines.filter(criteriafk__standardfk__sectionfk_id=filters['section'])
        if key == 'criterion' and filters['standard']: lines = lines.filter(criteriafk__standardfk_id=filters['standard'])
        detail_options[key+'_options'] = options(lines,path)
        # Apply earlier choices to dependent option lists; full selection below.
        if filters[key]:
            headers = headers.filter(pk__in=lines.filter(**{path+'_id':filters[key]}).values('header_id'))
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
              {'key':'facility_type','title':'Progress by facility type','label':'Facility types','rows':[]},
              {'key':'facility','title':'Progress by health facility','label':'Health facilities','detail':True,'rows':[]},
              {'key':'section','title':'Progress by section','label':'Sections','detail':True,'rows':[]},
              {'key':'standard','title':'Progress by standard','label':'Standards','detail':True,'rows':[]},
              {'key':'criterion','title':'Progress by verification criterion','label':'Verification criteria','detail':True,'rows':[]}]
    data = {**detail_options,'assessment_rows':[],'narrative_rows':[],'narrative_max_facilities':1,'criterion_evidence':[], 'filters':filters, 'province_options':provinces,'district_options':districts,
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
    data.update(assessment_details(selected,selected_rounds))
    raw = admin._hqip_standard_rows(selected)
    if filters['section']:raw = [r for r in raw if str(r['section_id'])==filters['section']]
    if filters['standard']:raw = [r for r in raw if str(r['standard_id'])==filters['standard']]
    if filters['criterion']:
        # Reaggregate only the chosen criterion; keep the established rollup hierarchy.
        raw = criterion_counts(selected, filters, None)
    meta = {fid:{'facility_type_id':tid,'facility_type':name or 'Unspecified'} for fid,tid,name in selected.values_list('facilityfk_id','facilityfk__facilitytypefk_id','facilityfk__facilitytypefk__name').distinct()}
    by_round = {r['id']:[] for r in selected_rounds}
    available = {rid:set() for rid in by_round}
    for row in raw:
        by_round[row['round_id']].append({**row,**meta[row['facility_id']]})
        if row['applicable']:
            available[row['round_id']].add((row['facility_id'],row['area_id']))
    matched = set.intersection(*available.values())
    observed = {rid:set(selected.filter(assessmenttype_id=rid).values_list('facilityfk_id','areafk_id')) for rid in by_round}
    for row in data['assessment_rows']:
        row['comparison_status'] = 'Included in matched cohort' if (row['facility_id'],row['area_id']) in matched else 'Excluded: no applicable match in every selected round'
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
        if group['key']=='criterion':continue
        key = 'area' if group['key']=='thematic' else group['key']
        buckets = defaultdict(lambda:defaultdict(list))
        names = {}
        for rid,rows in kept.items():
            for row in rows:
                gid = row[key+'_id']
                buckets[gid][rid].append(row)
                names[gid] = (' / '.join([row['area'],row['section']]+([row['standard']] if key=='standard' else [])) if key in ('section','standard') else row[key])
        for gid in sorted(buckets,key=lambda x:(names[x],x)):
            values = [admin._hqip_rollup_from_standard_rows(buckets[gid][r['id']])['overall_percent'] for r in selected_rounds]
            av,bv = values[0],values[-1]
            gain = admin._hqip_change(bv,av) if len(values)>1 else None
            group['rows'].append({'id':gid,'name':names[gid],'baseline':av,'comparison':bv,'gain':gain,
                                  'values':values,'baseline_width':str(av or 0),'comparison_width':str(bv or 0),
                                  'facilities':len({r['facility_id'] for r in buckets[gid][baseline['id']]}),
                                  'decline':gain is not None and gain<0})
    criterion_rows = criterion_counts(selected, filters, matched)
    cbuckets = defaultdict(dict)
    for row in criterion_rows:
        cbuckets[row['criterion_id']][row['round_id']] = row
    criterion_group = groups[-1]
    for cid, per_round in cbuckets.items():
        ref = next(iter(per_round.values()))
        values=[]; evidence=[]
        for r in selected_rounds:
            item = per_round.get(r['id'], {})
            score = admin._pct(item.get('yes',0),item.get('applicable',0))
            values.append(score)
            ev={'criterion_id':cid,'criterion':ref['criterion'],'area':ref['area'],'section':ref['section'],
                'standard':ref['standard'],'round':r['name'],'score':score,
                **{key:item.get(key,0) for key in ('yes','no','na','missing','applicable','facilities')}}
            evidence.append(ev);data['criterion_evidence'].append(ev)
        gain = admin._hqip_change(values[-1], values[0]) if len(values)>1 else None
        criterion_group['rows'].append({'id':cid,'name':' / '.join([ref['area'],ref['section'],ref['standard'],ref['criterion']]),
                'values':values,'baseline':values[0],'comparison':values[-1],'gain':gain,
                'facilities':max(e['facilities'] for e in evidence),'evidence':evidence,'decline':gain is not None and gain<0})
    criterion_group['rows'].sort(key=lambda r:r['name'])
    thematic = groups[0]['rows']
    data['largest_gain'] = max(thematic,key=lambda r:r['gain']) if thematic and len(selected_rounds)>1 else None
    data['highest_score'] = max(thematic,key=lambda r:r['comparison']) if thematic else None
    for group in groups:
        for row in group['rows']:
            row['scores']=[{'round':r['name'],'round_id':r['id'],'value':value,'width':str(value or 0),
                            'index':i} for i,(r,value) in enumerate(zip(selected_rounds,row['values']))]
    data['chart_payload'] = {'rounds':selected_rounds,'groups':[{'key':g['key'],'title':g['title'],'rows':[{k:r[k] for k in ('id','name','values')} for r in g['rows']]} for g in groups],'overall':overall_values}
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
        sheet = wb.create_sheet({'thematic':'Thematic areas','province':'Provinces','facility_type':'Facility types','facility':'Health facilities','section':'Sections','standard':'Standards','criterion':'Verification criteria'}[group['key']])
        sheet.append(['Group']+[r['name']+' (%)' for r in data['selected_rounds']]+['First-to-last gain (pp)','Matched facilities'])
        for r in group['rows']: sheet.append([r['name']]+r['values']+[r['gain'],r['facilities']])
    for title,key,columns in [
        ('Assessment details','assessment_rows',('round','province','district','facility_type','facility','area','start_date','end_date','assessor','team','implementor','rca','last_updated','comparison_status')),
        ('Assessment narrative','narrative_rows',('round','narrative','team_entries','assessors','implementors','facilities','headers','rca_yes','rca_no','rca_unspecified','team_entered','team_missing','team_percent')),
        ('Criteria evidence','criterion_evidence',('area','section','standard','criterion_id','criterion','round','yes','no','na','missing','applicable','score','facilities')),
    ]:
        sheet=wb.create_sheet(title);sheet.append([c.replace('_',' ').title() for c in columns])
        for row in data[key]:
            values=[]
            for c in columns:
                value=row.get(c)
                if isinstance(value,list):value=' | '.join(value)
                if hasattr(value,'utcoffset') and value.utcoffset() is not None:value=value.isoformat()
                values.append(value)
            sheet.append(values)
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


def criterion_counts(headers, filters, matched):
    """SQL aggregates; unknown scores follow the existing ID-based rules."""
    from .models import HQIPAssessment
    from .admin import SCORE_YES_ID, SCORE_NO_ID, SCORE_NA_ID
    from django.db.models import Count,F,Q
    qs=HQIPAssessment.objects.filter(header__in=headers,criteriafk__standardfk__sectionfk__areafk_id=F('header__areafk_id'))
    for key,path in (('section','criteriafk__standardfk__sectionfk_id'),('standard','criteriafk__standardfk_id'),('criterion','criteriafk_id')):
        if filters.get(key):qs=qs.filter(**{path:filters[key]})
    if matched is not None:
        by_area=defaultdict(set)
        for fid,aid in matched:by_area[aid].add(fid)
        condition=Q(pk__in=[])
        for aid,facilities in by_area.items():condition |= Q(header__areafk_id=aid,header__facilityfk_id__in=facilities)
        qs=qs.filter(condition)
    fields={'facility_id':'header__facilityfk_id','facility':'header__facilityfk__name','round_id':'header__assessmenttype_id',
            'province_id':'header__facilityfk__districtfk__provincefk_id','province':'header__facilityfk__districtfk__provincefk__name',
            'area_id':'criteriafk__standardfk__sectionfk__areafk_id','area':'criteriafk__standardfk__sectionfk__areafk__name',
            'section_id':'criteriafk__standardfk__sectionfk_id','section':'criteriafk__standardfk__sectionfk__name',
            'standard_id':'criteriafk__standardfk_id','standard':'criteriafk__standardfk__name',
            'criterion_id':'criteriafk_id','criterion':'criteriafk__name'}
    # When filtering a single criterion, facility-level rows are needed for cohort matching.
    if not filters.get('criterion') or matched is not None:
        fields.pop('facility_id');fields.pop('facility')
        fields.pop('province_id');fields.pop('province')
    rows=qs.order_by().values(**{key:F(path) for key,path in fields.items()}).annotate(
        yes=Count('pk',filter=Q(scorefk_id=SCORE_YES_ID)),no=Count('pk',filter=Q(scorefk_id=SCORE_NO_ID)),
        na=Count('pk',filter=Q(scorefk_id=SCORE_NA_ID)),missing=Count('pk',filter=Q(scorefk__isnull=True)),
        applicable=Count('pk',filter=Q(scorefk_id__in=[SCORE_YES_ID,SCORE_NO_ID])),
        facilities=Count('header__facilityfk_id',distinct=True))
    return list(rows)


def assessment_details(headers, rounds):
    """Factual narration generated from authorized existing header fields only."""
    from django.db.models import F
    rows=list(headers.order_by('assessmentdate','facilityfk__name','areafk__name','pk').values(
        'id','assessmentteam','assessmentdate','assessmentend_date','is_RCAduringtheassessment','updated_at',
        facility_id=F('facilityfk_id'),area_id=F('areafk_id'),round_id=F('assessmenttype_id'),round=F('assessmenttype__name'),
        province=F('facilityfk__districtfk__provincefk__name'),district=F('facilityfk__districtfk__name'),
        facility_type=F('facilityfk__facilitytypefk__name'),facility=F('facilityfk__name'),area=F('areafk__name'),
        assessor=F('assesorfk__name'),implementor=F('implementorfk__name')))
    for row in rows:
        row.update(team=(row.pop('assessmentteam') or '').strip() or 'ASSESSMENT TEAM NOT ENTERED',
                   start_date=row.pop('assessmentdate'),end_date=row.pop('assessmentend_date'),last_updated=row.pop('updated_at'),
                   comparison_status='Not included: no matched comparison available')
        rca=row.pop('is_RCAduringtheassessment')
        row['rca']='Yes' if rca is True else 'No' if rca is False else 'Not recorded'
    narratives=[]
    for r in rounds:
        items=[row for row in rows if row['round_id']==r['id']]
        if not items:continue
        starts=[x['start_date'] for x in items if x['start_date']]
        ends=[x['end_date'] for x in items if x['end_date']]
        date_text=(min(starts).strftime('%d %b %Y')+' to '+max(ends).strftime('%d %b %Y')) if starts and ends else 'dates incomplete'
        teams=sorted({x['team'] for x in items if x['team']!='ASSESSMENT TEAM NOT ENTERED'})
        assessors=sorted({x['assessor'] for x in items if x['assessor']})
        implementors=sorted({x['implementor'] for x in items if x['implementor']})
        missing=sum(x['team']=='ASSESSMENT TEAM NOT ENTERED' for x in items)
        text=(f"{r['name']}: {len({x['facility_id'] for x in items})} health facilities across "
              f"{len({x['province'] for x in items})} provinces and {len({x['area_id'] for x in items})} thematic areas "
              f"were represented in {len(items)} assessment headers. The recorded assessment period was {date_text}. "
              f"RCA was recorded as Yes in {sum(x['rca']=='Yes' for x in items)} headers, No in "
              f"{sum(x['rca']=='No' for x in items)} and not recorded in {sum(x['rca']=='Not recorded' for x in items)}. "
              f"Assessment team information was missing in {missing} headers. "
              f"Start or end dates were missing in {sum(not x['start_date'] or not x['end_date'] for x in items)} headers.")
        narratives.append({'round':r['name'],'narrative':text,'team_entries':teams,'assessors':assessors,'implementors':implementors,
            'facilities':len({x['facility_id'] for x in items}),'headers':len(items),
            'rca_yes':sum(x['rca']=='Yes' for x in items),'rca_no':sum(x['rca']=='No' for x in items),
            'rca_unspecified':sum(x['rca']=='Not recorded' for x in items),
            'team_entered':len(items)-missing,'team_missing':missing,
            'team_percent':round(100*(len(items)-missing)/len(items),2),
            'team_width':str(100*(len(items)-missing)/len(items)),
            'rca_yes_width':str(100*sum(x['rca']=='Yes' for x in items)/len(items)),
            'rca_no_width':str(100*sum(x['rca']=='No' for x in items)/len(items)),
            'rca_unspecified_width':str(100*sum(x['rca']=='Not recorded' for x in items)/len(items))})
    return {'assessment_rows':rows,'narrative_rows':narratives,'narrative_max_facilities':max([n['facilities'] for n in narratives]+[1])}

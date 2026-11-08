from io import BytesIO
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.http import urlencode
from .models import MenteeMatch
from .services import build_rows, enrich, permitted, scoped_people, source_models


@admin.register(MenteeMatch)
class MenteeMatchAdmin(admin.ModelAdmin):
    def has_view_permission(self, request, obj=None):
        return permitted(request.user)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_model_perms(self, request):
        return {'view': True} if permitted(request.user) else {}

    def get_urls(self):
        return [path('link/', self.admin_site.admin_view(self.link), name='mentee_comparison_link')] + super().get_urls()

    def can_link(self, request):
        return permitted(request.user) and request.user.has_perm('mentee_comparison.confirm_matches')

    def link(self, request):
        if request.method != 'POST':
            return HttpResponseBadRequest('Use the dashboard confirmation form.')
        if not self.can_link(request):
            raise PermissionDenied
        qs, qk, _ = scoped_people(request)
        try:
            sid = int(request.POST.get('staff', ''))
            kid = int(request.POST.get('skill', ''))
        except ValueError:
            return HttpResponseBadRequest('Choose both mentees.')
        s, k = qs.filter(pk=sid).first(), qk.filter(pk=kid).first()
        if not s or not k or (request.POST.get('action') == 'confirm' and s.hfname_id != k.hfname_id):
            raise PermissionDenied('Both mentees must be in the same authorized facility.')
        if request.POST.get('verified') != 'yes':
            return HttpResponseBadRequest('Confirm that you have checked both identities.')
        action = request.POST.get('action')
        if action not in ('confirm','remove'):
            return HttpResponseBadRequest('Unknown action.')
        try:
            with transaction.atomic():
                if action == 'remove':
                    match = MenteeMatch.objects.filter(staff=s, skill_mentee=k).first()
                    if match:
                        self.log_deletion(request, match, str(match))
                        match.delete()
                        messages.success(request, 'Comparison link removed. Session records are preserved.')
                else:
                    match = MenteeMatch.objects.create(staff=s, skill_mentee=k,
                        confirmed_by=request.user, note=request.POST.get('note','')[:500])
                    self.log_addition(request,match,'Confirmed mentee comparison link after identity review.')
                    messages.success(request,'Mentees linked. Their actual sessions can now be compared.')
        except IntegrityError:
            messages.error(request,'One of these mentees is already linked. Review the confirmed pairs first.')
        url = reverse('admin:mentee_comparison_menteematch_changelist', current_app=self.admin_site.name)
        return HttpResponseRedirect(url + '?' + urlencode({'q':s.firstname,'state':'all'}))

    def changelist_view(self, request, extra_context=None):
        if not permitted(request.user):
            raise PermissionDenied
        try:
            rows, counts, options, pid = build_rows(request)
            if request.GET.get('export') == 'xlsx':
                return self.export(enrich(rows,request.GET,pid), request)
            page = Paginator(rows,20).get_page(request.GET.get('page',1))
            page.object_list = enrich(list(page.object_list),request.GET,pid)
        except ValidationError as exc:
            return HttpResponseBadRequest('; '.join(exc.messages))
        _, qk, _ = scoped_people(request)
        by_facility = {}
        for person in qk.order_by('firstname','id'):
            by_facility.setdefault(person.hfname_id,[]).append(person)
        for row in page.object_list:
            row['manual_options'] = by_facility.get(row['s'].hfname_id,[]) if row['s'] else []
        params = request.GET.copy()
        params.pop('page',None)
        params.pop('export',None)
        context = {**self.admin_site.each_context(request), 'title':'Mentorship & Skill Lab | Mentee comparison',
            'opts':self.model._meta, 'page':page, 'counts':dict(counts), 'options':options,
            'filters':request.GET, 'selected_state':request.GET.get('state','confirmed'),
            'query':params.urlencode(), 'can_link':self.can_link(request),
            'link_url':reverse('admin:mentee_comparison_link', current_app=self.admin_site.name),
            'has_view_permission':True, **(extra_context or {})}
        request.current_app = self.admin_site.name
        return TemplateResponse(request,'admin/mentee_comparison/dashboard.html',context)

    def export(self, rows, request):
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
        wb = Workbook()
        wb.remove(wb.active)
        def sheet(name, headings):
            ws=wb.create_sheet(name)
            ws.append(headings)
            return ws
        def safe(value):
            if isinstance(value,str) and value.startswith(('=','+','-','@')):
                return "'"+value
            return value
        def add(ws,values):
            ws.append([safe(v) for v in values])
        pairs=sheet('Mentee comparison',['Match status','Mentorship ID','Mentorship name','Father name','Province','Facility','Position','Gender','Active','Skill Lab ID','Skill Lab name','Skill Lab father','Skill Lab facility','Skill Lab position','Skill Lab gender','Skill Lab active','Confirmed by ID','Confirmed on','Match note'])
        topics=sheet('Topics',['Mentorship ID','Skill Lab ID','Area','Topic','Definition','Alignment','Coverage','Mentorship LS','Mentorship PC','Mentorship MC','Skill Lab LS','Skill Lab PC','Skill Lab MC','Mentorship first','Mentorship latest','Skill Lab first','Skill Lab latest'])
        areas=sheet('Thematic areas',['Mentorship ID','Skill Lab ID','Area','Mentorship LS','Mentorship PC','Mentorship MC','Skill Lab LS','Skill Lab PC','Skill Lab MC'])
        sessions=sheet('Actual records',['Mentorship ID','Skill Lab ID','Source','Record ID','Date','Facility','Mentor','Area','Topic','Session flags','Quality note'])
        suggestions=sheet('Possible matches',['Mentorship ID','Skill Lab ID','Skill Lab name','Father name','Position','Reason','Already linked'])
        meta=sheet('Read me',['Item','Value'])
        add(meta,['Filters',request.GET.urlencode()])
        add(meta,['Scope','Only confirmed pairs have session comparisons. Dates filter sessions, not identity matching. Provincial users see only sessions recorded in their authorized province.'])
        add(meta,['Interpretation','Counts are actual record flags, not competency certification. PC is not collected in Skill Lab. Unmapped topics are kept separate.'])
        for row in rows:
            s,k,p=row['s'],row['k'],row['person']
            link=row['link']
            add(pairs,[row['state'],getattr(s,'pk',None),str(s or ''),getattr(s,'fathername',''),str(p.hfname.districtfk.provincefk),str(p.hfname),str(p.position),p.get_gender_display(),p.get_status_display(),getattr(k,'pk',None),str(k or ''),getattr(k,'fathername',''),str(k.hfname) if k else '',str(k.position) if k else '',k.get_gender_display() if k else '',k.get_status_display() if k else '',getattr(link,'confirmed_by_id',None),str(link.confirmed_at) if link else '',getattr(link,'note','')])
            for c in row['candidates']:
                add(suggestions,[s.pk,c['person'].pk,str(c['person']),c['person'].fathername,str(c['person'].position),c['reason'],c['linked']])
            for t in row['topics']:
                add(topics,[s.pk,k.pk,t['area'],t['topic'],t['definition'],t['mapping'],t['coverage'],t['m_ls'],t['m_pc'],t['m_mc'],t['k_ls'],'Not collected',t['k_mc'],t['m_first'],t['m_last'],t['k_first'],t['k_last']])
            for a in row['areas']:
                add(areas,[s.pk,k.pk,a['name'],a['m_ls'],a['m_pc'],a['m_mc'],a['k_ls'],'Not collected',a['k_mc']])
            for e in row['sessions']:
                add(sessions,[s.pk,k.pk,e['source'],e['id'],e['date'],e['facility'],e['mentor'],e['area'],e['topic'],e['type'],e['quality']])
        for ws in wb:
            ws.freeze_panes='A2'
            ws.auto_filter.ref=ws.dimensions
            for cell in ws[1]:
                cell.font=Font(bold=True,color='FFFFFF')
                cell.fill=PatternFill('solid',fgColor='006B54')
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width=min(60,max(16,max(len(str(c.value or '')) for c in col)+2))
        data=BytesIO()
        wb.save(data)
        response=HttpResponse(data.getvalue(),content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition']='attachment; filename="Mentee_Comparison.xlsx"'
        return response

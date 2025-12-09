import openpyxl
from django.http import HttpResponse
from django.contrib import admin
from django import forms
from django.db import connection
from django.utils.translation import gettext_lazy as _
from .models import aimpee, aimpph, Gancenrollment, Gancfirstsession,Gancsecondsession, Gancthirdsession, Gancohort, Mpdsr, Qicdataset, Qiccriterialist, tpm, Qqmdomain, QqmdomainIndicator, Participantposition, Participanteducation, Trainingheader, Indicator, IndicatorType, ProjectGoal, ProjectObjective, ProjectOutput, Position, Staff, Standards, Section,Score, Criteria, Area, Assessmenttype, Province, District, Facility, Facilitytype, Implementor, Assessor, Mentorshipvisit, Assessment, Training, Participationtype, ThematicMentorship, MentorshipTopics, Mentorshipvisit, Mentorshipdetails  
from .forms import AimpeeAdminForm, AimpphAdminForm

admin.site.site_header = "Maternal and Newborn Information Management System (MNIMS)"
admin.site.site_title = "Health Admin Portal"
admin.site.index_title = "M&E Data Management System"

class ProvinceFilter(admin.SimpleListFilter):
    title = "Province"
    parameter_name = "province"

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        provinces = qs.values_list(
            "aimfacilityname__districtfk__provincefk__id",
            "aimfacilityname__districtfk__provincefk__name",
        ).distinct()
        return [
            (pid, pname) for pid, pname in provinces if pid is not None
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                aimfacilityname__districtfk__provincefk__id=self.value()
            )
        return queryset


class DistrictFilter(admin.SimpleListFilter):
    title = "District"
    parameter_name = "district"

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        districts = qs.values_list(
            "aimfacilityname__districtfk__id",
            "aimfacilityname__districtfk__name",
        ).distinct()
        return [
            (did, dname) for did, dname in districts if did is not None
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                aimfacilityname__districtfk__id=self.value()
            )
        return queryset

@admin.register(aimpee)
class AimpeeAdmin(admin.ModelAdmin):
    form = AimpeeAdminForm
    list_display = (
        "id",
        "get_province",
        "aimfacilityname",   # real field (dropdown)
        "shamsiyear",
        "shamsimonth",
        "period",
        "bl_progress",
        "gre_year",
        "gre_month",
        "afiat_flag",
        "num_anc_preg_seen",
        "num_anc_bp_taken",
        "num_anc_pree_dx",
        "num_severe_pe_e_bp160",
        "num_severe_pe_e_bp160_tx1h",
        "num_anc_pree_admit",
        "num_spe_admit_before_delivery",
        "num_eclampsia_admit_before_delivery",
        "num_spe_e_mgso4_1h",
        "num_spe_at_birth",
        "num_eclampsia_at_birth",
        "num_chronic_htn_superimposed_pe",
        "num_gest_htn",
        "num_spe_deliv_24h",
        "num_eclampsia_deliv_12h",
        "num_spe_e_fu_3d",
        "num_spe_e_pp_dx",      
    )

    fieldsets = (
        # 🔹 TOP NON-COLLAPSIBLE
        ("AIM-PEE Record Information", {
            "classes": ("wide",),
            "fields": (
                "aimfacilityname", # dropdown from model (Facility FK)
                "shamsiyear",
                "shamsimonth",
                "period",
                "bl_progress",
                "gre_year",
                "gre_month",
                "afiat_flag",
            ),
        }),

        # 🔻 Collapsible groups (only if these fields exist on this model)
        ("ANC / Pre-E core indicators", {
            "classes": ("collapse",),
            "fields": (
                "num_anc_preg_seen",
                "num_anc_bp_taken",
                "num_anc_pree_dx",
                "num_severe_pe_e_bp160",
                "num_severe_pe_e_bp160_tx1h",
                "num_anc_pree_admit",
                "num_spe_admit_before_delivery",
                "num_eclampsia_admit_before_delivery",
                "num_spe_e_mgso4_1h",
                "num_spe_at_birth",
                "num_eclampsia_at_birth",
                "num_chronic_htn_superimposed_pe",
                "num_gest_htn",
                "num_spe_deliv_24h",
                "num_eclampsia_deliv_12h",
                "num_spe_e_fu_3d",
                "num_spe_e_pp_dx",
            ),
        }),
        ("Complications due to SPE / Eclampsia", {
            "classes": ("collapse",),
            "fields": (
                "comp_renal_failure",
                "comp_pulmonary_edema",
                "comp_eclamptic_seizure",
                "comp_stroke",
                "comp_thrombocytopenia",
                "comp_hellp",
                "comp_pres",
                "comp_iufd",
                "comp_placental_abruption",
                "comp_eclamptic_coma",
                "comp_total",
                "maternal_death_spe_e",
            ),
        }),
        ("Outpatient / OPD management", {
            "classes": ("collapse",),
            "fields": (
                "num_opd_pree_dx_md",
                "num_opd_pree_twice_week",
                "num_opd_pree_weekly_labs",
                "pct_opd_pree_weekly_labs",
            ),
        }),
        ("Advanced interventions", {
            "classes": ("collapse",),
            "fields": (
                "ai_aortic_compression",
                "ai_ubt",
                "ai_lac_repair",
                "ai_blynch_ual",
                "ai_nasg",
                "ai_ruptured_uterus_repair",
                "ai_pph_hysterectomy",
                "ai_hysterectomy_other",
                "ai_total",
            ),
        }),
    )

      # 👇 Filters on the right side in admin
    list_filter = (
        ProvinceFilter,
        DistrictFilter,
        "aimfacilityname",   # Facility filter (built-in)
    )

    @admin.display(description="Facility Name")
    def get_facility_name(self, obj):
        return obj.aimfacilityname.name   # Adjust if your Facility model uses a different field

    @admin.display(description="Province")
    def get_province(self, obj):
        return obj.aimfacilityname.districtfk.provincefk.name
    

@admin.register(aimpph)
class AimpphAdmin(admin.ModelAdmin):
    form = AimpphAdminForm
    list_display = (
        "id",
        "get_province",
        "aimfacilityname",   # real field (dropdown)
        "shamsiyear",
        "shamsimonth",
        "period",
        "bl_progress",
        "gre_year",
        "gre_month",
        "afiat_flag",
        "total_births",
        "births_vaginal",
        "births_csection",
        "pph_vaginal_501_999",
        "pph_cs_1000_plus",
        "maternal_death_pph_transfer",
        "ai_total",
    )

    readonly_fields = ("get_province",)

    @admin.display(description="Province")
    def get_province(self, obj):
        # adjust field names if needed, but this matches your Facility → District → Province chain
        return obj.aimfacilityname.districtfk.provincefk.name

    fieldsets = (
        # ⭐ TOP SECTION (always visible)
        ("AIM-PPH Record Information", {
            "classes": ("wide",),
            "fields": (
                "aimfacilityname",
                "shamsiyear",
                "shamsimonth",
                "period",
                "bl_progress",
                "gre_year",
                "gre_month",
                "afiat_flag",
            ),
        }),

        # 1️⃣ Births & early care
        ("Births & Oxytocin", {
            "classes": ("collapse",),
            "fields": (
                "total_births",
                "births_vaginal",
                "births_csection",
                "oxytocin_immediate",
                "antepartum_hemorrhage",
            ),
        }),

        # 2️⃣ PPH categories + QBL breakdown
        ("PPH Categories & QBL", {
            "classes": ("collapse",),
            "fields": (
                "pph_vaginal_501_999",
                "pph_cs_1000_plus",
                "pph_referral_in_outside_aim",
                "pph_referral_in_aim",
                "qbl_0_500",
                "qbl_501_999",
                "qbl_1000_1499",
                "qbl_1500_1999",
                "qbl_2000_2499",
                "qbl_2500_plus",
                "qbl_unknown",
                "qbl_total",
                "transfers_out_pph",
                "maternal_death_pph_transfer",
                "maternal_death_other_transfer",
                "maternal_death_total_transfer",
            ),
        }),

        # 3️⃣ Causes of PPH
        ("Causes of PPH", {
            "classes": ("collapse",),
            "fields": (
                "cause_uterine_atony",
                "cause_severe_lacerations",
                "cause_retained_products",
                "cause_dic",
                "cause_ruptured_uterus",
                "cause_abruption",
                "cause_placenta_previa",
                "cause_placenta_accreta",
                "cause_other",
                "cause_unknown",
                "causes_total",
            ),
        }),

        # 4️⃣ Advanced clinical interventions
        ("Advanced Interventions", {
            "classes": ("collapse",),
            "fields": (
                "ai_uterine_compression",
                "ai_manual_placenta",
                "ai_aortic_compression",
                "ai_ubt",
                "ai_lac_repair",
                "ai_blynch_ual",
                "ai_nasg",
                "ai_ruptured_uterus_repair",
                "ai_pph_hysterectomy",
                "ai_hysterectomy_other",
                "ai_total",
            ),
        }),
    )
      # 👇 Filters on the right side in admin
    list_filter = (
        ProvinceFilter,
        DistrictFilter,
        "aimfacilityname",   # Facility filter (built-in)
    )

class QICMonthFilter(admin.SimpleListFilter):
    title = _('QI Committee Date (Month + Year)')
    parameter_name = 'qic_month'

    def lookups(self, request, model_admin):
        dates = (Qicdataset.objects
                 .exclude(qiccommdate__isnull=True)
                 .dates('qiccommdate', 'month'))
        return [(d.strftime("%Y-%m"), d.strftime("%B %Y")) for d in dates]

    def queryset(self, request, queryset):
        if self.value():
            year, month = self.value().split('-')
            return queryset.filter(qiccommdate__year=year, qiccommdate__month=month)
        return queryset

class MyModelqicdataset(admin.ModelAdmin):
    list_display = ['id', 'qiccommdate','qicfacility','qicdatacollector','qicimplementor','qictoravailvalue',
                    'qiclastmonthvalue', 'qicmmavialvalue', 'qicmmsignedvalue', 'qicmmdatausevalue',
                    'qichqiptollavailvalue', 'qicpipavailvalue', 'qicpipupdatedvalue','qicngoinvolvedvalue',
                    'qicpeertopeeravailvalue', 'qicmenteelogbookavialvalue','qicmenteelogbookupdatedvalue',
                    'qicmetwithhealthshuravalue','qichealthshurainvolvedincorractvalue',
                    'qictotalquestions','image']
    list_filter = ['qicfacility', QICMonthFilter, 'qicfacility__districtfk__provincefk']  # Add filter for parent
    # search_fields = ['name']  # Search child name and parent name
    list_per_page = 20  # Set pagination (10 rows per page)
    actions = ['duplicate_QIC']

    @admin.action(description="Duplicate selected QIC")
    def duplicate_QIC(self, request, queryset):
        for obj in queryset:
            # Create a copy of the object
            obj.pk = None  # Set primary key to None to create a new object
            obj.name = f"{obj.qiccommdate} (Copy)"  # Optional: mark it as a copy
            obj.save()
        self.message_user(request, f"{queryset.count()} QIC(s) duplicated successfully.")

class MyModeltpm(admin.ModelAdmin):
    list_display = ['id', 'auditdate','facility','domainindicator','score']
    list_filter = ['facility']  # Add filter for parent
    # search_fields = ['name']  # Search child name and parent name
    list_per_page = 10  # Set pagination (10 rows per page)

class MyModelIndicator(admin.ModelAdmin):
    list_display = ['id', 'name','indicatortype','indicatoroutput','datasource', 
                    'baseline','target','achivement', 'remarks','indicatormodality']
    list_filter = ['indicatoroutput']  # Add filter for parent
    search_fields = ['name']  # Search child name and parent name
    list_per_page = 5  # Set pagination (10 rows per page)

class MyModelArea(admin.ModelAdmin):
    list_display = ['id', 'name','shortname']
    # list_filter = ['areafk']  # Add filter for parent
    # search_fields = ['name']  # Search child name and parent name
    # list_per_page = 10  # Set pagination (10 rows per page)

class MyModelStandard(admin.ModelAdmin):
    list_display = ['id', 'sectionfk','name', 'shortname']
    list_filter = ['sectionfk']  # Add filter for parent
    search_fields = ['name']  # Search child name and parent name
    list_per_page = 10  # Set pagination (10 rows per page)

class MyModelSection(admin.ModelAdmin):
    list_display = ['id', 'areafk','name', 'shortname']
    list_filter = ['areafk']  # Add filter for parent
    search_fields = ['name']  # Search child name and parent name
    list_per_page = 10  # Set pagination (10 rows per page)

class MyModelProvince(admin.ModelAdmin):
    list_display = ['id', 'name','description', 'province','provinceDari','provincePashto',
                    'provincecode','provinceshortname','phase']
    # list_filter = ['thematicfk']  # Add filter for parent
    search_fields = ['name']  # Search child name and parent name
    list_per_page = 10  # Set pagination (10 rows per page)

class MyModelMentorshiptopics(admin.ModelAdmin):
    list_display = ['id', 'thematicfk','name', 'shortname']
    list_filter = ['thematicfk']  # Add filter for parent
    search_fields = ['name']  # Search child name and parent name
    list_per_page = 10  # Set pagination (10 rows per page)

class MyModelCriteria(admin.ModelAdmin):
    list_display = [
        'id',
        'get_area',
        'get_section',
        'standardfk',
        'name',
        #'shortname',
        'namedari',
        'scorefk',
    ]
    class Media:
        js = ('js/admin_resizable.js',)  # relative to static files
    
    list_filter = [
        'standardfk__sectionfk__areafk',
        'standardfk__sectionfk',
        'standardfk',
    ]
    search_fields = [
        'name',
        'standardfk__name',
        'standardfk__sectionfk__name',
        'standardfk__sectionfk__areafk__name',
    ]
    list_per_page = 10

    def get_section(self, obj):
        return obj.standardfk.sectionfk.name
    get_section.short_description = 'Section'

    def get_area(self, obj):
        return obj.standardfk.sectionfk.areafk.name
    get_area.short_description = 'Area'

class MyModelDistricts(admin.ModelAdmin):
    list_display = ['id', 'name','description', 'provincefk','district', 'districtcode',
                    'districtdari', 'districtpashto']
    list_filter = ['provincefk']  # Add filter for parent
    search_fields = ['name']  # Search child name and parent name
    list_per_page = 10  # Set pagination (10 rows per page)

class MyModelAssesors(admin.ModelAdmin):
    list_display = ['id', 'name','contact', 'email','gender', 'tazkira', 'implementer', 
                    'province', 'Status', 'phaseonecloseout', 'continuetophase2', 'note']
    list_filter = ['province']  # Add filter for parent
    search_fields = ['name']  # Search child name and parent name
    list_per_page = 10  # Set pagination (10 rows per page)

class MyModelHfstaff(admin.ModelAdmin):
    list_display = ['id', 'firstname','lastname', 'tazkiranumber','gender', 'status', 'hfname'
                     , 'position']
    list_filter = ['hfname_id']  # Add filter for parent
    search_fields = ['firstname']  # Search child name and parent name
    list_per_page = 10  # Set pagination (10 rows per page)

class ProvinceFilter(admin.SimpleListFilter):
    title = 'Province'
    parameter_name = 'province'

    def lookups(self, request, model_admin):
        provinces = Province.objects.all()
        return [(p.id, p.name) for p in provinces]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(districtfk__provincefk__id=self.value())
        return queryset

class MyModelAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'get_province', 'get_phase', 'districtfk', 'name', 'hfcode', 
        'facilitytypefk', 'skilllab', 'aim', 'aimphase', 'safesurgery', 
        'ganc', 'afiat'
    ]
    
    list_filter = [
        'districtfk__provincefk__phase',   # Phase first
        ProvinceFilter,                    # Province second (custom filter)
        'facilitytypefk'                   # Facility type third
    ]
    
    search_fields = ['name', 'districtfk__name', 'districtfk__provincefk__name']
    list_per_page = 15
    ordering = ['districtfk__provincefk__name', 'districtfk__name']

    @admin.display(description='Province')
    def get_province(self, obj):
        return obj.districtfk.provincefk.name

    @admin.display(description='Phase')
    def get_phase(self, obj):
        return obj.districtfk.provincefk.phase

class MyModelAdminHqip(admin.ModelAdmin):
    list_display = ['id', 'assessmentdate','areafk', 'sectionfk', 'standardfk',
                    'assesorfk','assessmenttype', 
                    'criteriafk', 'scorefk',
                    'facilityfk',
                     'implementorfk']
    list_filter = ['areafk', 'facilityfk']  # Add filter for parent
    # search_fields = ['criteriafk']  # Search child name and parent name
    list_per_page = 15  # Set pagination (10 rows per page)

    # Custom action to export to Excel
    def export_to_excel(self, request, queryset):
        # Create an Excel workbook
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Exported Data"
        
        # Write the header row
        headers = ['id', 'assessment date','area fk', 'assesor fk','assessment type', 'criteria fk', 'facility fk'
                     , 'implementor fk', 'score fk', 'section fk', 'standard fk']
        sheet.append(headers)
        
        # Write data rows
        for obj in queryset:
            row = [
                str(obj.id) if obj.id is not None else '', 
                str(obj.assessmentdate) if obj.assessmentdate is not None else '', 
                str(obj.areafk) if obj.areafk is not None else '', 
                str(obj.assesorfk) if obj.assesorfk is not None else '',
                str(obj.assessmenttype) if obj.assessmenttype is not None else '', 
                str(obj.criteriafk) if obj.criteriafk is not None else '', 
                str(obj.facilityfk) if obj.facilityfk is not None else '',
                str(obj.implementorfk) if obj.implementorfk is not None else '', 
                str(obj.scorefk) if obj.areafk is not None else '', 
                str(obj.sectionfk) if obj.sectionfk is not None else '', 
                str(obj.standardfk) if obj.standardfk is not None else ''
                ]
            sheet.append(row)
        
        # Create a response to download the Excel file
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = 'attachment; filename="exported_data.xlsx"'
        workbook.save(response)
        return response
    
    export_to_excel.short_description = "Export to Excel"  # Name of the action
    
    # Register the action
    actions = [export_to_excel]

class Trainingdetails(admin.StackedInline):  # Use StackedInline for a different layout
    model = Training
    extra = 1  # Number of empty rows for adding new items

@admin.register(Trainingheader)
class TrainingAdmin(admin.ModelAdmin):
    inlines = [Trainingdetails]
    list_display = ("trainingname", "trainingvenue", "trainingstartdate", "trainingenddate", 
                    "remarks","expectednumberofparticipant","traingfocalpoint")
    search_fields = ("trainingname",)

class mpdsrshow(admin.ModelAdmin):
    # inlines = [OrderItemInline]
    list_display = ["id", "yearmpdsr",
        "monthmpdsr",
        "facilityname",
        "n_mpdsrcommittee",
        "n_maternaldeathreported",
        "n_maternaldeathreviewed",
        "causeofmaternaldeaths_m",
        "nastillbirthreportedreported",
        "nastillbirthreportedreviewed",
        "nistillbirthreported",
        "nistillbirthreviewed",
        "nndeath_afteralivebirth_reported",
        "nndeath_afteralivebirth_reviewed"]
        #"causeofneonataldeath_n",
        #"interventionperformed",
        #"recfromMPDSRcommittee",
        #"remarks",
        #"uploaded_at"]
    list_filter = ['monthmpdsr', 'facilityname__districtfk__provincefk']  # Add filter for parent

class ganccohorts(admin.ModelAdmin):
    # inlines = [OrderItemInline]
    list_display = ("facilityname", "cohortname", "cohortnumber",
                    "cohortstatus", "cohortchecklist", "cohortcreatedby", "remarks")
    list_filter = ['facilityname', 'facilityname__districtfk__provincefk' ]  # Add filter for parent

class gancenrollment(admin.ModelAdmin):
    # inlines = [OrderItemInline]
    list_display = ("id","cohortname", "enrollmentid", "name", "fathername",
                    "contactnumber", "address", "gafirstanc", "edd", "remarks" )
    list_filter = ['cohortname']  # Add filter for parent

class gancfirstsession(admin.ModelAdmin):
    # inlines = [OrderItemInline]
    list_display = ("registerid","sessiontype", "sessionround","sessiondate","attendance",
                    "presentga", "bp", "dhypertension","rhypertensiontoMD",
                    "weight","anemia","ironfolate","ironfolatepluswomen",
                    "pcalcium","acalcium","muac","dmam","rmam","dsam","rsam",
                    "clabexm","hemoglobin","urinexam","rpositivepuriatomd","coughmorethantwoweeks",
                    "rcough","ttvaccine", "dangersign", "typeofdangersign", "remarks")
    list_filter = ['sessiondate', 'sessionround']  # Add filter for parent
    # search_fields = ['criteriafk']  # Search child name and parent name
    list_per_page = 10  # Set pagination (10 rows per page)
    #list_filter = ['facilityname']  # Add filter for parent

class MentorshipdetailsInlineForm(forms.ModelForm):
    class Meta:
        model = Mentorshipdetails
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # Initialize the form first

        if self.instance.pk:  # Editing existing record
            self.fields['menteename'].queryset = Staff.objects.filter(hfname=self.instance.mentorshipvistfk.facilityfk)
        else:  # Adding new record
            self.fields['menteename'].queryset = Staff.objects.none()  # Show empty dropdown initially

class MentorshipdetailsInline(admin.TabularInline):  # Display mentees in a table
    model = Mentorshipdetails
    form = MentorshipdetailsInlineForm
    extra = 0  # No extra blank rows

    def get_extra(self, request, obj=None, **kwargs):
        """Ensure correct number of mentees appear when editing"""
        if obj:
            return max(1, Staff.objects.filter(hfname=obj.facilityfk).count())  # At least one row
        return 0  # Show nothing when adding a new record

    def get_queryset(self, request):
        """Ensure mentee filtering works correctly"""
        queryset = super().get_queryset(request)
        if request.resolver_match.kwargs.get("object_id"):  # Editing an existing visit
            mentorship_visit = Mentorshipvisit.objects.get(id=request.resolver_match.kwargs["object_id"])
            return queryset.filter(mentorshipvistfk=mentorship_visit)
        return queryset.none()  # When adding a new visit, show nothing
    
@admin.register(Mentorshipvisit)
class MentorshipvisitAdmin(admin.ModelAdmin):
    inlines = [MentorshipdetailsInline]
    list_display = ("id", "facilityfk", "visitdate", "visitround", "mentorshipstarttime", "mentorshipendtime")
    list_filter = ['facilityfk__districtfk__provincefk__name']
    search_fields = ("visitdate",)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Dynamically filter the menteename field based on the selected facility"""
        if db_field.name == "menteename":
            obj_id = request.resolver_match.kwargs.get("object_id")
            if obj_id:
                mentorship_visit = Mentorshipvisit.objects.get(id=obj_id)
                kwargs["queryset"] = Staff.objects.filter(hfname=mentorship_visit.facilityfk)
            else:
                kwargs["queryset"] = Staff.objects.none()  # Empty when adding a new record
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def export_mentorship_to_excel(modeladmin, request, queryset):
        # Extract the filtered Mentorshipvisit IDs from the queryset
        visit_ids = queryset.values_list('id', flat=True)

        if not visit_ids:
            modeladmin.message_user(request, "No records selected or filtered to export.")
            return

        # Convert IDs to comma-separated string
        id_list_str = ",".join([str(id) for id in visit_ids])

        # Raw SQL query with WHERE clause limited to selected IDs
        query = f"""
        SELECT
            T1.ID, T1.VISITROUND, T1.VISITDATE, T1.MENTORSHIPSTARTTIME, T1.MENTORSHIPENDTIME,
            T10.NAME AS Province, T9.NAME AS District, T4.NAME AS "HF Name",
            T11.NAME AS FacilityType, T11.ID AS facilitytypeID,
            T3.NAME AS Mentor, T2.ID, T2.LS, T2.PC, T2.MC,
            T5.ID AS topicId, T5.SHORTNAME AS Topic,
            T6.ID AS ThematicId, T6.NAME AS Thematic,
            T7.ID AS menteeId, T7.FIRSTNAME AS MenteeName, T7.GENDER AS MenteeGender,
            T8.ID AS professionId, T8.NAME AS MenteeProfession,
            DATE_PART('Year', T1.VISITDATE) AS year,
            DATE_PART('Month', T1.VISITDATE) AS month,
            DATE_PART('Day', T1.VISITDATE) AS day
        FROM HIVA_MENTORSHIPVISIT T1
        INNER JOIN HIVA_MENTORSHIPDETAILS T2 ON T1.ID = T2.MENTORSHIPVISTFK_ID
        INNER JOIN HIVA_ASSESSOR T3 ON T3.ID = T2.MENTOR_ID
        INNER JOIN HIVA_FACILITY T4 ON T4.ID = T1.FACILITYFK_ID
        INNER JOIN HIVA_MENTORSHIPTOPICS T5 ON T5.ID = T2.TOPICNAME_ID
        INNER JOIN HIVA_THEMATICMENTORSHIP T6 ON T6.ID = T2.THEMATICNAME_ID
        INNER JOIN HIVA_STAFF T7 ON T7.ID = T2.MENTEENAME_ID
        INNER JOIN HIVA_POSITION T8 ON T8.ID = T7.POSITION_ID
        INNER JOIN HIVA_DISTRICT T9 ON T9.ID = T4.DISTRICTFK_ID
        INNER JOIN HIVA_PROVINCE T10 ON T10.ID = T9.PROVINCEFK_ID
        INNER JOIN HIVA_FACILITYTYPE T11 ON T11.ID = T4.FACILITYTYPEFK_ID
        WHERE T1.ID IN ({id_list_str})
        """

        with connection.cursor() as cursor:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()

        # Generate Excel workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Filtered Export"
        ws.append(columns)

        for row in rows:
            row = list(row)
            # Convert LS, PC, MC to 1/0 — assuming they are at fixed positions
            # Adjust indices if needed; here, they are at index 12, 13, 14
            for i in [12, 13, 14]:
                if isinstance(row[i], bool):
                    row[i] = int(row[i])
            ws.append(row)

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = 'attachment; filename="filtered_mentorship_export.xlsx"'
        wb.save(response)
        return response

    actions = [export_mentorship_to_excel]
    
# Register your models here.
admin.site.register(Score)
admin.site.register(Criteria, MyModelCriteria)
admin.site.register(Section, MyModelSection)
admin.site.register(Standards, MyModelStandard)
admin.site.register(Area, MyModelArea)
admin.site.register(Assessmenttype)
admin.site.register(Province, MyModelProvince)
admin.site.register(District, MyModelDistricts)
admin.site.register(Facility, MyModelAdmin)
admin.site.register(Facilitytype)
admin.site.register(Implementor)
admin.site.register(Assessor, MyModelAssesors)
admin.site.register(Assessment, MyModelAdminHqip)
admin.site.register(Training)
admin.site.register(Participationtype)
admin.site.register(ThematicMentorship)
admin.site.register(MentorshipTopics, MyModelMentorshiptopics)
admin.site.register(Position)
admin.site.register(Staff, MyModelHfstaff)
admin.site.register(ProjectGoal)
admin.site.register(ProjectObjective)
admin.site.register(ProjectOutput)
admin.site.register(IndicatorType)
admin.site.register(Indicator, MyModelIndicator)
admin.site.register(Participantposition)
admin.site.register(Participanteducation)
admin.site.register(Qqmdomain)
admin.site.register(QqmdomainIndicator)
admin.site.register(tpm, MyModeltpm)
admin.site.register(Qicdataset, MyModelqicdataset)
admin.site.register(Qiccriterialist)
admin.site.register(Mpdsr, mpdsrshow)
admin.site.register(Gancohort, ganccohorts)
admin.site.register(Gancenrollment, gancenrollment)
admin.site.register(Gancfirstsession, gancfirstsession)
admin.site.register(Gancsecondsession)
admin.site.register(Gancthirdsession)


import openpyxl
from django.http import HttpResponse, response
from django.contrib import admin
from django import forms
from django.db import connection
from django.utils.translation import gettext_lazy as _
from .models import (
    HQIPAssessmentHeader, 
    safesurgeryclinical, 
    aimpee, 
    aimpph, 
    Mpdsr, 
    Qicdataset, 
    Participantposition, 
    Participanteducation, 
    Trainingheader, 
    Standards, 
    Section,
    Score, 
    Criteria, 
    Area, 
    Assessmenttype, 
    Province, 
    District, 
    Facility, 
    Facilitytype, 
    Implementor, Assessor, HQIPAssessment, Training, Participationtype, Position)  
from .forms import AimpeeAdminForm, AimpphAdminForm
from decimal import Decimal, InvalidOperation
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import UserProfile
from hiva.admin_utils import user_province
from django.urls import path
from django.http import JsonResponse
from django.db import transaction
from django.forms.models import BaseInlineFormSet
from hiva.admin_utils import ProvinceRestrictedAdminMixin, user_province
from django.utils import timezone
from django.template.response import TemplateResponse
from django.db.models import Count, Q
from django.utils.html import format_html
from django.urls import reverse
from collections import defaultdict
from django.urls import path
from django.shortcuts import render
from django.utils.timezone import now
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict
from django.db.models import Q, Count
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from django.db.models import Count, Q
from collections import defaultdict
from datetime import datetime

admin.site.site_header = "Maternal and Newborn Health Information Management System (MNHIMS)"
admin.site.site_title = "IQoC Portal"
admin.site.index_title = "M&E Data Management System"

class ProvinceFromFacilityFilter(admin.SimpleListFilter):
    title = "Province"
    parameter_name = "province"

    # override in subclasses
    province_path = None  # e.g. "facilityfk__districtfk__provincefk"

    def lookups(self, request, model_admin):
        if not self.province_path:
            return []

        qs = model_admin.get_queryset(request)

        provinces = qs.values_list(
            f"{self.province_path}__id",
            f"{self.province_path}__name",
        ).distinct().order_by(f"{self.province_path}__name")

        return [(pid, pname) for pid, pname in provinces if pid]

    def queryset(self, request, queryset):
        if self.value() and self.province_path:
            return queryset.filter(**{f"{self.province_path}__id": self.value()})
        return queryset

class AimpeeProvinceFilter(admin.SimpleListFilter):
    title = "Province"
    parameter_name = "province"

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        provinces = qs.values_list(
            "aimfacilityname__districtfk__provincefk__id",
            "aimfacilityname__districtfk__provincefk__name",
        ).distinct().order_by("aimfacilityname__districtfk__provincefk__name")

        return [(pid, pname) for pid, pname in provinces if pid]
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                aimfacilityname__districtfk__provincefk__id=self.value()
            )
        return queryset

class AimpeeFacilityFilter(admin.SimpleListFilter):
    title = "Facility"
    parameter_name = "facility"

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)

        # If province filter selected, limit facilities to that province
        prov_id = request.GET.get("province")
        if prov_id:
            qs = qs.filter(aimfacilityname__districtfk__provincefk__id=prov_id)

        facilities = qs.values_list("aimfacilityname__id", "aimfacilityname__name") \
                       .distinct().order_by("aimfacilityname__name")

        return [(fid, fname) for fid, fname in facilities if fid]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(aimfacilityname__id=self.value())
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
class AimpeeAdmin(ProvinceRestrictedAdminMixin, admin.ModelAdmin):
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
        #AimpeeFacilityFilter,
        DistrictFilter,
        AimpeeFacilityFilter,   # Facility filter (built-in)
    )
    
    @admin.display(description="Facility Name")
    def get_facility_name(self, obj):
        return obj.aimfacilityname.name   # Adjust if your Facility model uses a different field

    @admin.display(description="Province")
    def get_province(self, obj):
        return obj.aimfacilityname.districtfk.provincefk.name
    
    def province_filter_kwargs(self, request):
        return {"aimfacilityname__districtfk__provincefk": request.user.profile.province}

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # limit facility dropdown for province users
        if db_field.name == "aimfacilityname" and not request.user.is_superuser:
            prov = user_province(request)
            if prov:
                kwargs["queryset"] = Facility.objects.filter(districtfk__provincefk=prov)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(aimpph)
class AimpphAdmin(ProvinceRestrictedAdminMixin, admin.ModelAdmin):
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
        # AimpeeProvinceFilter,
        DistrictFilter,
        AimpeeFacilityFilter,   # Facility filter (built-in)
    )

    def province_filter_kwargs(self, request):
        return {"aimfacilityname__districtfk__provincefk": request.user.profile.province}

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "aimfacilityname" and not request.user.is_superuser:
            prov = user_province(request)
            if prov:
                kwargs["queryset"] = Facility.objects.filter(districtfk__provincefk=prov)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(safesurgeryclinical)
class CSectionSafeSurgeryAdmin(ProvinceRestrictedAdminMixin, admin.ModelAdmin):
    form = AimpeeAdminForm
    list_display = (
        "id",
        "get_province",
        "aimfacilityname",
        "shamsiyear",
        "shamsimonth",
        "period",
        "total_cs",
        "total_deliv",
        "cs_rate",
        "who_ssc_rate",
        "safe_tracker_rate",
        "pph_cs_rate",
        "qbl_cs_rate",
        "postop_fever_rate",
        "hyst_rate",
        "mat_death_total",
    )

    # ⭐ Make all rate fields readonly (auto-calculated)
    readonly_fields = (
        "cs_rate",
        "who_ssc_rate",
        "safe_tracker_rate",
        "pph_cs_rate",
        "qbl_cs_rate",
        "postop_fever_rate",
        "bladder_injury_rate",
        "bowel_injury_rate",
        "hyst_rate",
        "vag_clean_rate",
        "foley_after_anes_rate",
        "abx_proph_rate",
        "skin_prep_rate",
    )

    list_filter = (
        #AimpeeFacilityFilter,
        DistrictFilter,
        AimpeeFacilityFilter,   # Facility filter (built-in)
    )

    # Grouped, collapsible fieldsets
    fieldsets = (
        # ⭐ TOP SECTION (always visible, context)
        (
            "AIM-PPH Record Information",
            {
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
            },
        ),
        (
            "Core Volumes",
            {
                "fields": (
                    "total_cs",
                    "total_deliv",
                    "cs_rate",
                ),
            },
        ),
        (
            "Process Indicators – Checklists & Trackers",
            {
                "classes": ("collapse",),
                "fields": (
                    "who_ssc_completed",
                    "who_ssc_rate",
                    "safe_tracker_complete",
                    "safe_tracker_rate",
                ),
            },
        ),
        (
            "Process Indicators – Perioperative Practices",
            {
                "classes": ("collapse",),
                "fields": (
                    "vag_clean_num",
                    "vag_clean_rate",
                    "foley_after_anes_num",
                    "foley_after_anes_rate",
                    "abx_proph_num",
                    "abx_proph_rate",
                    "skin_prep_num",
                    "skin_prep_rate",
                ),
            },
        ),
        (
            "Complications During / After C-Section",
            {
                "classes": ("collapse",),
                "fields": (
                    "pph_cs_num",
                    "pph_cs_rate",
                    "qbl_cs_num",
                    "qbl_cs_rate",
                    "postop_fever_num",
                    "postop_fever_rate",
                    "bladder_injury_num",
                    "bladder_injury_rate",
                    "bowel_injury_num",
                    "bowel_injury_rate",
                    "hyst_num",
                    "hyst_rate",
                ),
            },
        ),
        (
            "Maternal Deaths (CS-related and other)",
            {
                "classes": ("collapse",),
                "fields": (
                    "mat_death_pph_cs",
                    "mat_death_other_cs",
                    "mat_death_total",
                ),
            },
        ),
    )

    # 🔢 Helper to safely compute percentages
    def _pct(self, num, den):
        try:
            if num is None or den in (None, 0):
                return None
            return (Decimal(num) / Decimal(den)) * Decimal("100.0")
        except (InvalidOperation, ZeroDivisionError):
            return None

    # 💾 Auto-calculate all rate fields before saving
    def save_model(self, request, obj, form, change):
        # Core CS rate
        obj.cs_rate = self._pct(obj.total_cs, obj.total_deliv)

        # Checklists & trackers – denominator: total_cs
        obj.who_ssc_rate = self._pct(obj.who_ssc_completed, obj.total_cs)
        obj.safe_tracker_rate = self._pct(obj.safe_tracker_complete, obj.total_cs)

        # Complications – denominator: total_cs
        obj.pph_cs_rate = self._pct(obj.pph_cs_num, obj.total_cs)
        obj.qbl_cs_rate = self._pct(obj.qbl_cs_num, obj.total_cs)
        obj.postop_fever_rate = self._pct(obj.postop_fever_num, obj.total_cs)
        obj.bladder_injury_rate = self._pct(obj.bladder_injury_num, obj.total_cs)
        obj.bowel_injury_rate = self._pct(obj.bowel_injury_num, obj.total_cs)
        obj.hyst_rate = self._pct(obj.hyst_num, obj.total_cs)

        # Perioperative practices – denominator: total_cs
        obj.vag_clean_rate = self._pct(obj.vag_clean_num, obj.total_cs)
        obj.foley_after_anes_rate = self._pct(obj.foley_after_anes_num, obj.total_cs)
        obj.abx_proph_rate = self._pct(obj.abx_proph_num, obj.total_cs)
        obj.skin_prep_rate = self._pct(obj.skin_prep_num, obj.total_cs)

        super().save_model(request, obj, form, change)

        readonly_fields = ("get_province",)

    @admin.display(description="Province")
    def get_province(self, obj):
        # adjust field names if needed, but this matches your Facility → District → Province chain
        return obj.aimfacilityname.districtfk.provincefk.name

    def province_filter_kwargs(self, request):
        return {"aimfacilityname__districtfk__provincefk": request.user.profile.province}

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "aimfacilityname" and not request.user.is_superuser:
            prov = user_province(request)
            if prov:
                kwargs["queryset"] = Facility.objects.filter(districtfk__provincefk=prov)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

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
    list_display = ['id', 'name','shortname', 'area_namepashto', 'area_namedari']
    # list_filter = ['areafk']  # Add filter for parent
    # search_fields = ['name']  # Search child name and parent name
    # list_per_page = 10  # Set pagination (10 rows per page)

class MyModelStandard(admin.ModelAdmin):
    list_display = ['id', 'sectionfk','name', 'shortname','standard_namepashto','standard_namedari']
    list_filter = ['sectionfk']  # Add filter for parent
    search_fields = ['name']  # Search child name and parent name
    list_per_page = 10  # Set pagination (10 rows per page)

class MyModelSection(admin.ModelAdmin):
    list_display = ['id', 'areafk','name', 'shortname', 'section_namepashto','section_namedari']
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
        'criteria_namepashto',
        'criteria_namedari',
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
                    'province', 'phaseonecloseout', 'continuetophase2', 'note']
    list_filter = ['province']  # Add filter for parent
    search_fields = ['name']  # Search child name and parent name
    list_per_page = 10  # Set pagination (10 rows per page)

class ModelMentees(admin.ModelAdmin):
    list_display = ['id', 'hfname','firstname', 'lastname','position', 'tazkiranumber', 'gender']
    list_filter = ['hfname']  # Add filter for parent
    search_fields = ['firstname']  # Search child name and parent name
    list_per_page = 10  # Set pagination (10 rows per page)

class ModelMentorshipdetails(admin.ModelAdmin):
    list_display = ['id', 'mentorshipvistfk','menteename', 'thematicname','topicname', 'mentor', 'ls', 
                    'pc', 'mc', 'image', 'uploaded_at']
    list_filter = ['mentorshipvistfk']  # Add filter for parent
    search_fields = ['menteename']  # Search child name and parent name
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

@admin.register(Facility)
class FacilityAdmin(ProvinceRestrictedAdminMixin, admin.ModelAdmin):
    list_display = [
        'id', 'get_province', 'districtfk', 'name', 'hfcode',
        'facilitytypefk', 'skilllab', 'aim', 'aimphase', 'safesurgery', 
        'ganc', 'afiat', 'nbcc','sncu','kmc'
    ]
    list_filter = ['districtfk__provincefk', 'facilitytypefk']
    search_fields = ['name', 'districtfk__name', 'districtfk__provincefk__name']
    list_per_page = 15

    def province_filter_kwargs(self, request):
        return {"districtfk__provincefk": request.user.profile.province}
    
    @admin.display(description="Province")
    def get_province(self, obj):
        return obj.districtfk.provincefk.name

    @admin.display(description="Phase")
    def get_phase(self, obj):
        return obj.districtfk.provincefk.phase

class AssessmentLineForm(forms.ModelForm):
    class Meta:
        model = HQIPAssessment
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("scorefk"):
            raise forms.ValidationError("Score is required for every criterion.")
        return cleaned

class RequiredScoreInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            if form.cleaned_data.get("DELETE"):
                continue
            if not form.cleaned_data.get("scorefk"):
                raise forms.ValidationError("Please fill score for all criteria before saving.")

class AssessmentLineInline(admin.TabularInline):
    model = HQIPAssessment
    extra = 0
    can_delete = False
    show_change_link = False
    form = AssessmentLineForm
    formset = RequiredScoreInlineFormSet

    # show read-only context + editable score
    fields = ("get_section", "get_standard", "get_criteria", "scorefk")
    readonly_fields = ("get_section", "get_standard", "get_criteria")

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related(
            "header",
            "header__facilityfk__districtfk__provincefk",
            "criteriafk",
            "criteriafk__standardfk",
            "criteriafk__standardfk__sectionfk",
            "scorefk",
        ).order_by(
            "criteriafk__standardfk__sectionfk__id",
            "criteriafk__standardfk__id",
            "criteriafk__id",
        )

        # Province restriction (optional but safe)
        if request.user.is_superuser:
            return qs

        prov = user_province(request)
        if not prov:
            return qs.none()

        return qs.filter(header__facilityfk__districtfk__provincefk=prov)

    @admin.display(description="Section")
    def get_section(self, obj):
        if obj.criteriafk_id:
            return obj.criteriafk.standardfk.sectionfk.name
        return "-"

    @admin.display(description="Standard")
    def get_standard(self, obj):
        if obj.criteriafk_id:
            return obj.criteriafk.standardfk.name
        return "-"

    @admin.display(description="Criteria")
    def get_criteria(self, obj):
        return obj.criteriafk.name if obj.criteriafk_id else "-"

    def has_add_permission(self, request, obj=None):
        return False
    
# Score PK mapping in your system:
SCORE_YES_ID = 1
SCORE_NO_ID = 2
SCORE_NA_ID = 3

@admin.register(HQIPAssessmentHeader)
class AssessmentHeaderAdmin(ProvinceRestrictedAdminMixin, admin.ModelAdmin):
    inlines = [AssessmentLineInline]

    list_display = (
        "id",
        "facilityfk",
        "assessmenttype",
        "assessmentdate",
        "assessmentend_date",
        "areafk",
        "assesorfk",
        "hqip_dashboard_button",
        "hqip_facility_button",
        "created_by",
        "created_at",
    )
    list_filter = ("areafk", "facilityfk")
    search_fields = ("facilityfk__name", "facilityfk__hfcode")

    # ---------------------------
    # Province restriction (mix-in)
    # ---------------------------
    def province_filter_kwargs(self, request):
        return {"facilityfk__districtfk__provincefk": request.user.profile.province}

    # ---------------------------
    # Helpers (safe rounding / %)
    # ---------------------------
    def _round2(self, x):
        if x is None:
            return None
        return float(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    def _pct(self, yes_count, applicable_count):
        if not applicable_count:
            return None
        return self._round2((Decimal(yes_count) / Decimal(applicable_count)) * Decimal(100))

    # ---------------------------
    # Dashboard URLs (admin pages)
    # ---------------------------
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "hqip-standards-dashboard/",
                self.admin_site.admin_view(self.hqip_standards_dashboard),
                name="hqip_standards_dashboard",
            ),
            path(
                "hqip-facility-dashboard/",
                self.admin_site.admin_view(self.hqip_facility_dashboard),
                name="hqip_facility_dashboard",
            ),
        ]
        return custom_urls + urls

    # ---------------------------
    # Buttons in list_display
    # ---------------------------
    @admin.display(description="Standards Dashboard")
    def hqip_dashboard_button(self, obj):
        url = reverse("admin:hqip_standards_dashboard")
        return format_html('<a class="button" href="{}">HQIP Dashboard</a>', url)

    @admin.display(description="Facility Drill-down")
    def hqip_facility_button(self, obj):
        url = reverse("admin:hqip_facility_dashboard")
        return format_html('<a class="button" href="{}">Facility Drill-down</a>', url)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["hqip_dashboard_url"] = reverse("admin:hqip_standards_dashboard")
        extra_context["hqip_facility_url"] = reverse("admin:hqip_facility_dashboard")
        return super().changelist_view(request, extra_context=extra_context)

    # ==========================================================
    # A) GLOBAL DASHBOARD: Standard -> Section -> Area
    # ==========================================================
    def hqip_standards_dashboard(self, request):
        """
        Produces 3 KPIs:
        1) Standard % = YES / (YES+NO) * 100   (NA excluded)
        2) Section % = average(Standard %)
        3) Area % = average(Section %)
        """

        # Province users: restricted by mixin
        headers_qs = self.get_queryset(request)

        # Superuser optional province filter
        selected_province = request.GET.get("province")
        if request.user.is_superuser and selected_province:
            headers_qs = headers_qs.filter(
                facilityfk__districtfk__provincefk_id=selected_province
            )

        std_rows = (
            HQIPAssessment.objects
            .filter(header__in=headers_qs)
            .values(
                "criteriafk__standardfk__id",
                "criteriafk__standardfk__name",
                "criteriafk__standardfk__sectionfk__id",
                "criteriafk__standardfk__sectionfk__name",
                "criteriafk__standardfk__sectionfk__areafk__id",
                "criteriafk__standardfk__sectionfk__areafk__name",
            )
            .annotate(
                yes=Count("id", filter=Q(scorefk_id=SCORE_YES_ID)),
                applicable=Count("id", filter=Q(scorefk_id__in=[SCORE_YES_ID, SCORE_NO_ID])),
            )
            .order_by(
                "criteriafk__standardfk__sectionfk__areafk__name",
                "criteriafk__standardfk__sectionfk__name",
                "criteriafk__standardfk__name",
            )
        )

        standard_results = []
        section_to_standard_percents = defaultdict(list)

        # Build name maps safely (single pass)
        sec_name_map = {}
        area_name_map = {}

        for r in std_rows:
            area_id = r["criteriafk__standardfk__sectionfk__areafk__id"]
            sec_id = r["criteriafk__standardfk__sectionfk__id"]
            sec_key = (area_id, sec_id)

            area_name = r["criteriafk__standardfk__sectionfk__areafk__name"] or "-"
            sec_name = r["criteriafk__standardfk__sectionfk__name"] or "-"

            sec_name_map[sec_key] = (area_name, sec_name)
            area_name_map[area_id] = area_name

            den = r["applicable"]
            num = r["yes"]
            std_percent = self._pct(num, den)

            standard_results.append({
                "area": area_name,
                "section": sec_name,
                "standard": r["criteriafk__standardfk__name"] or "-",
                "yes": num,
                "applicable": den,
                "percent": std_percent,
            })

            if std_percent is not None:
                section_to_standard_percents[sec_key].append(std_percent)

        # SECTION % = average(Standard %)
        section_results = []
        area_to_section_percents = defaultdict(list)

        for sec_key, percents in section_to_standard_percents.items():
            area_id, _sec_id = sec_key
            area_name, sec_name = sec_name_map.get(sec_key, ("-", "-"))

            sec_percent = None
            if percents:
                sec_percent = self._round2(sum(percents) / len(percents))

            section_results.append({
                "area": area_name,
                "section": sec_name,
                "num_standards_used": len(percents),
                "percent": sec_percent,
            })

            if sec_percent is not None:
                area_to_section_percents[area_id].append(sec_percent)

        section_results.sort(key=lambda x: (x["area"], x["section"]))

        # AREA % = average(Section %)
        area_results = []
        for area_id, percents in area_to_section_percents.items():
            area_percent = None
            if percents:
                area_percent = self._round2(sum(percents) / len(percents))

            area_results.append({
                "area": area_name_map.get(area_id, "-"),
                "num_sections_used": len(percents),
                "percent": area_percent,
            })

        area_results.sort(key=lambda x: x["area"])

        provinces = Province.objects.all().order_by("name") if request.user.is_superuser else None

        context = dict(
            self.admin_site.each_context(request),
            title="HQIP Dashboard – Standard / Section / Area Achievement (%)",
            standard_results=standard_results,
            section_results=section_results,
            area_results=area_results,
            provinces=provinces,
            selected_province=selected_province,
        )
        return TemplateResponse(request, "admin/hiva/hqip_dashboard_full.html", context)

    # ==========================================================
    # B) FACILITY DRILL-DOWN DASHBOARD
    # ==========================================================
    def hqip_facility_dashboard(self, request):
        """
        Facility-level drill-down:
        - Facility dropdown ALWAYS shows facilities user can access (even if no HQIP headers exist yet).
        - When facility selected, calculate Standard/Section/Area using the same NA exclusion logic.
        """

        # ---------- read filters ----------
        selected_province = request.GET.get("province")  # superuser only
        selected_facility = request.GET.get("facility")
        selected_area = request.GET.get("area")
        selected_type = request.GET.get("assessmenttype")
        date_from = request.GET.get("date_from")
        date_to = request.GET.get("date_to")

        # ---------- build FACILITY queryset (IMPORTANT FIX) ----------
        facilities_qs = Facility.objects.all().select_related("districtfk__provincefk")

        # Province restriction for non-superuser
        if not request.user.is_superuser:
            prov = user_province(request)
            if prov:
                facilities_qs = facilities_qs.filter(districtfk__provincefk=prov)
            else:
                facilities_qs = facilities_qs.none()

        # Superuser optional province filter
        if request.user.is_superuser and selected_province:
            facilities_qs = facilities_qs.filter(districtfk__provincefk_id=selected_province)

        facilities = facilities_qs.order_by("name")

        # ---------- areas/types for dropdowns ----------
        areas = Area.objects.all().order_by("name")
        types = Assessmenttype.objects.all().order_by("name")
        provinces = Province.objects.all().order_by("name") if request.user.is_superuser else None

        # ---------- if no facility selected -> only show filters ----------
        facility_obj = None
        header_list = []
        standard_results, section_results, area_results = [], [], []

        std_chart_json, sec_chart_json = [], []

        if selected_facility:
            facility_obj = Facility.objects.filter(pk=selected_facility).select_related(
                "districtfk__provincefk"
            ).first()

            # Security: ensure user can only open allowed facility
            if facility_obj:
                if (not request.user.is_superuser) and (facility_obj.districtfk.provincefk != user_province(request)):
                    facility_obj = None  # block access safely

        if facility_obj:
            # ---------- build header queryset from allowed headers ----------
            headers_qs = self.get_queryset(request).filter(facilityfk=facility_obj)

            if selected_area:
                headers_qs = headers_qs.filter(areafk_id=selected_area)

            if selected_type:
                headers_qs = headers_qs.filter(assessmenttype_id=selected_type)

            # Date filter (safe parsing)
            if date_from:
                try:
                    headers_qs = headers_qs.filter(assessmentdate__gte=date_from)
                except Exception:
                    pass
            if date_to:
                try:
                    headers_qs = headers_qs.filter(assessmentdate__lte=date_to)
                except Exception:
                    pass

            header_list = list(headers_qs.values("id", "assessmentdate"))

            # ---------- aggregate STANDARD level ----------
            std_rows = (
                HQIPAssessment.objects
                .filter(header__in=headers_qs)
                .values(
                    "criteriafk__standardfk__id",
                    "criteriafk__standardfk__name",
                    "criteriafk__standardfk__sectionfk__id",
                    "criteriafk__standardfk__sectionfk__name",
                    "criteriafk__standardfk__sectionfk__areafk__id",
                    "criteriafk__standardfk__sectionfk__areafk__name",
                )
                .annotate(
                    yes=Count("id", filter=Q(scorefk_id=SCORE_YES_ID)),
                    applicable=Count("id", filter=Q(scorefk_id__in=[SCORE_YES_ID, SCORE_NO_ID])),
                )
                .order_by(
                    "criteriafk__standardfk__sectionfk__areafk__name",
                    "criteriafk__standardfk__sectionfk__name",
                    "criteriafk__standardfk__name",
                )
            )

            section_to_standard_percents = defaultdict(list)
            area_to_section_percents = defaultdict(list)
            sec_name_map = {}
            area_name_map = {}

            # Standard results list
            for r in std_rows:
                den = r["applicable"]
                num = r["yes"]
                std_percent = round((num / den) * 100, 2) if den else None

                standard_results.append({
                    "area": r["criteriafk__standardfk__sectionfk__areafk__name"],
                    "section": r["criteriafk__standardfk__sectionfk__name"],
                    "standard": r["criteriafk__standardfk__name"],
                    "yes": num,
                    "applicable": den,
                    "percent": std_percent,
                })

                area_id = r["criteriafk__standardfk__sectionfk__areafk__id"]
                sec_id = r["criteriafk__standardfk__sectionfk__id"]
                sec_key = (area_id, sec_id)

                sec_name_map[sec_key] = (
                    r["criteriafk__standardfk__sectionfk__areafk__name"],
                    r["criteriafk__standardfk__sectionfk__name"],
                )
                area_name_map[area_id] = r["criteriafk__standardfk__sectionfk__areafk__name"]

                if std_percent is not None:
                    section_to_standard_percents[sec_key].append(std_percent)

            # Section results
            for sec_key, percents in section_to_standard_percents.items():
                area_id, sec_id = sec_key
                area_name, sec_name = sec_name_map.get(sec_key, ("-", "-"))
                sec_percent = round(sum(percents) / len(percents), 2) if percents else None

                section_results.append({
                    "area": area_name,
                    "section": sec_name,
                    "num_standards_used": len(percents),
                    "percent": sec_percent,
                })

                if sec_percent is not None:
                    area_to_section_percents[area_id].append(sec_percent)

            section_results.sort(key=lambda x: (x["area"], x["section"]))

            # Area results
            for area_id, percents in area_to_section_percents.items():
                area_percent = round(sum(percents) / len(percents), 2) if percents else None
                area_results.append({
                    "area": area_name_map.get(area_id, "-"),
                    "num_sections_used": len(percents),
                    "percent": area_percent,
                })

            area_results.sort(key=lambda x: x["area"])

            # JSON for charts (no template tags inside JS)
            std_chart_json = [
                {"label": r["standard"], "value": r["percent"]}
                for r in standard_results
                if r.get("percent") is not None
            ]
            sec_chart_json = [
                {"label": r["section"], "value": r["percent"]}
                for r in section_results
                if r.get("percent") is not None
            ]

        context = dict(
            self.admin_site.each_context(request),
            title="HQIP Facility Drill-Down",
            provinces=provinces,
            selected_province=selected_province,

            facilities=facilities,
            selected_facility=selected_facility,
            facility_obj=facility_obj,

            areas=areas,
            selected_area=selected_area,

            types=types,
            selected_type=selected_type,

            date_from=date_from,
            date_to=date_to,

            header_list=header_list,
            standard_results=standard_results,
            section_results=section_results,
            area_results=area_results,

            std_chart_json=std_chart_json,
            sec_chart_json=sec_chart_json,
        )

        return TemplateResponse(request, "admin/hiva/hqip_facility_dashboard.html", context)


#@admin.register(HQIPAssessment)
class HQIPAssessmentAdmin(ProvinceRestrictedAdminMixin, admin.ModelAdmin):
    list_display = ("id", "header", "criteriafk", "scorefk")
    search_fields = ("criteriafk__name", "header__facilityfk__name")
    list_select_related = ("header", "header__facilityfk__districtfk__provincefk", "criteriafk", "scorefk")

    def province_filter_kwargs(self, request):
        return {"header__facilityfk__districtfk__provincefk": request.user.profile.province}

# class MyModelAdminHqip(admin.ModelAdmin):
#     list_display = ['id', 'assessmentdate','areafk', 'sectionfk', 'standardfk',
#                     'assesorfk','assessmenttype', 
#                     'criteriafk', 'scorefk',
#                     'facilityfk',
#                      'implementorfk']
#     list_filter = ['areafk', 'facilityfk']  # Add filter for parent
#     # search_fields = ['criteriafk']  # Search child name and parent name
#     list_per_page = 15  # Set pagination (10 rows per page)

#     # Custom action to export to Excel
#     def export_to_excel(self, request, queryset):
#         # Create an Excel workbook
#         workbook = openpyxl.Workbook()
#         sheet = workbook.active
#         sheet.title = "Exported Data"
        
#         # Write the header row
#         headers = ['id', 'assessment date','area fk', 'assesor fk','assessment type', 'criteria fk', 'facility fk'
#                      , 'implementor fk', 'score fk', 'section fk', 'standard fk']
#         sheet.append(headers)
        
#         # Write data rows
#         for obj in queryset:
#             row = [
#                 str(obj.id) if obj.id is not None else '', 
#                 str(obj.assessmentdate) if obj.assessmentdate is not None else '', 
#                 str(obj.areafk) if obj.areafk is not None else '', 
#                 str(obj.assesorfk) if obj.assesorfk is not None else '',
#                 str(obj.assessmenttype) if obj.assessmenttype is not None else '', 
#                 str(obj.criteriafk) if obj.criteriafk is not None else '', 
#                 str(obj.facilityfk) if obj.facilityfk is not None else '',
#                 str(obj.implementorfk) if obj.implementorfk is not None else '', 
#                 str(obj.scorefk) if obj.areafk is not None else '', 
#                 str(obj.sectionfk) if obj.sectionfk is not None else '', 
#                 str(obj.standardfk) if obj.standardfk is not None else ''
#                 ]
#             sheet.append(row)
        
#         # Create a response to download the Excel file
#         response = HttpResponse(
#             content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
#         )
#         response['Content-Disposition'] = 'attachment; filename="exported_data.xlsx"'
#         workbook.save(response)
#         return response
    
#     export_to_excel.short_description = "Export to Excel"  # Name of the action
    
#     # Register the action
#     actions = [export_to_excel]

class Trainingdetails(admin.StackedInline):  # Use StackedInline for a different layout
    model = Training
    extra = 1  # Number of empty rows for adding new items

@admin.register(Trainingheader)
class TrainingAdmin(admin.ModelAdmin):
    inlines = [Trainingdetails]
    list_display = ("trainingname", "trainingvenue", "trainingstartdate", "trainingenddate", 
                    "remarks","expectednumberofparticipant","traingfocalpoint")
    search_fields = ("trainingname",)

class MpdsrProvinceFilter(ProvinceFromFacilityFilter):
    province_path = "facilityname__districtfk__provincefk"

@admin.register(Mpdsr)
class mpdsrshow(ProvinceRestrictedAdminMixin, admin.ModelAdmin):
    list_display = ["id", 
        "yearmpdsr",
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

    list_filter = [MpdsrProvinceFilter, 'monthmpdsr']  # Add filter for parent
    search_fields = ("facilityname__name", "facilityname__districtfk__name", "facilityname__districtfk__provincefk__name")

    def province_filter_kwargs(self, request):
        return {"facilityname__districtfk__provincefk": request.user.profile.province}

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "facilityname" and not request.user.is_superuser:
            prov = user_province(request)
            if prov:
                kwargs["queryset"] = Facility.objects.filter(districtfk__provincefk=prov)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
    
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
   
#@admin.register(Mentorshipvisit)
class MentorshipvisitAdmin(admin.ModelAdmin):
    list_display = ("id", "facilityfk", "visitdate", "visitround")
    list_filter = ("facilityfk__districtfk__provincefk__name",)

    def mentees_for_facility(self, request):
        facility_id = request.GET.get("facility_id")

        if not facility_id:
            return JsonResponse({"results": []})

        # province restriction
        if not request.user.is_superuser:
            prov = user_province(request)
            if prov:
                if not Facility.objects.filter(
                    id=facility_id,
                    districtfk__provincefk=prov
                ).exists():
                    return JsonResponse({"results": []})

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "facilityfk" and not request.user.is_superuser:
            prov = user_province(request)
            if prov:
                kwargs["queryset"] = Facility.objects.filter(
                    districtfk__provincefk=prov
                )
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

User = get_user_model()

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    fk_name = "user"          # important: explicit OneToOne link
    can_delete = False
    extra = 1
    max_num = 1

class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # ensure exists (safe)
        # UserProfile.objects.get_or_create(user=obj)

def has_approve_rights(user):
    return user.is_superuser or user.groups.filter(name="Approvers").exists()

def get_actions(self, request):
    actions = super().get_actions(request)
    if not has_approve_rights(request.user):
        actions.pop("approve_selected", None)
        actions.pop("reject_selected", None)
    return actions

# Register your models here.
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(Score)
admin.site.register(Criteria, MyModelCriteria)
admin.site.register(Section, MyModelSection)
admin.site.register(Standards, MyModelStandard)
admin.site.register(Area, MyModelArea)
admin.site.register(Assessmenttype)
admin.site.register(Province, MyModelProvince)
admin.site.register(District, MyModelDistricts)
admin.site.register(Facilitytype)
admin.site.register(Implementor)
admin.site.register(Assessor, MyModelAssesors)
admin.site.register(Training)
admin.site.register(Participationtype)
admin.site.register(Participantposition)
admin.site.register(Participanteducation)
admin.site.register(Qicdataset, MyModelqicdataset)
admin.site.register(Position)



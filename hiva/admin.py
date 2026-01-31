from urllib.parse import urlencode
import openpyxl
from django.http import HttpResponse
from openpyxl.utils import get_column_letter
from django.http import HttpResponse
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict
from django.contrib import admin
from django.db import transaction
from django.db.models import Count, Q
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from urllib.parse import urlencode
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime
from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db import connection, transaction
from django.db.models import Count, Q
from django.forms.models import BaseInlineFormSet
from django.http import HttpResponse, JsonResponse
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .forms import AimpeeAdminForm, AimpphAdminForm
from .models import (
    HQIPAssessmentHeader,
    HQIPAssessment,
    Score,
    Criteria,
    Standards,
    Section,
    Area,
    Assessmenttype,
    Province,
    District,
    Facility,
    Facilitytype,
    Implementor,
    Assessor,
    UserProfile,
    safesurgeryclinical,
    aimpee,
    aimpph,
    Mpdsr,
    Qicdataset,
    Participantposition,
    Participanteducation,
    Trainingheader,
    Training,
    Participationtype,
    Position,
    WhoChildbirthChecklistMonthly,
)
from django.utils.http import urlencode
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError

# ============================================================
# Admin Branding
# ============================================================
admin.site.site_header = "Maternal and Newborn Health Information Management System (MNHIMS)"
admin.site.site_title = "IQoC Portal"
admin.site.index_title = "M&E Data Management System"

class HQIPProvinceFilter(admin.SimpleListFilter):
    title = "Province"
    parameter_name = "province"

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)

        rows = qs.values_list(
            "facilityfk__districtfk__provincefk__id",
            "facilityfk__districtfk__provincefk__name",
        ).distinct().order_by(
            "facilityfk__districtfk__provincefk__name"
        )

        return [(pid, pname) for pid, pname in rows if pid]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                facilityfk__districtfk__provincefk_id=self.value()
            )
        return queryset

# ============================================================
# Province helper (supports user.profile OR user.userprofile)
# ============================================================

def user_province(request):
    if request.user.is_superuser:
        return None
    profile = getattr(request.user, "profile", None) or getattr(request.user, "userprofile", None)
    return getattr(profile, "province", None)

class ProvinceRestrictedAdminMixin:
    """
    Universal restriction for province-based access.
    Subclasses must implement:
      - province_filter_kwargs(request) -> dict of filters
    """

    def province_filter_kwargs(self, request):
        raise NotImplementedError

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        prov = user_province(request)
        if prov is None:
            return qs.none()
        return qs.filter(**self.province_filter_kwargs(request))

    def _obj_in_scope(self, request, obj):
        return self.get_queryset(request).filter(pk=obj.pk).exists()

    def has_view_permission(self, request, obj=None):
        base = super().has_view_permission(request, obj=obj)
        if not base:
            return False
        if obj is None or request.user.is_superuser:
            return True
        return self._obj_in_scope(request, obj)

    def has_change_permission(self, request, obj=None):
        base = super().has_change_permission(request, obj=obj)
        if not base:
            return False
        if obj is None or request.user.is_superuser:
            return True
        return self._obj_in_scope(request, obj)

    def has_delete_permission(self, request, obj=None):
        base = super().has_delete_permission(request, obj=obj)
        if not base:
            return False
        if obj is None or request.user.is_superuser:
            return True
        return self._obj_in_scope(request, obj)

# ============================================================
# Reusable filters
# ============================================================

class ProvinceFromFacilityFilter(admin.SimpleListFilter):
    title = "Province"
    parameter_name = "province"
    province_path = None  # override in subclasses

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

class DistrictFilter(admin.SimpleListFilter):
    title = "District"
    parameter_name = "district"

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        districts = qs.values_list(
            "aimfacilityname__districtfk__id",
            "aimfacilityname__districtfk__name",
        ).distinct()
        return [(did, dname) for did, dname in districts if did is not None]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(aimfacilityname__districtfk__id=self.value())
        return queryset

class AimpeeFacilityFilter(admin.SimpleListFilter):
    title = "Facility"
    parameter_name = "facility"

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        prov_id = request.GET.get("province")
        if prov_id:
            qs = qs.filter(aimfacilityname__districtfk__provincefk__id=prov_id)

        facilities = qs.values_list("aimfacilityname__id", "aimfacilityname__name").distinct().order_by("aimfacilityname__name")
        return [(fid, fname) for fid, fname in facilities if fid]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(aimfacilityname__id=self.value())
        return queryset

# ============================================================
# AIM-PEE
# ============================================================
@admin.register(aimpee)
class AimpeeAdmin(ProvinceRestrictedAdminMixin, admin.ModelAdmin):
    form = AimpeeAdminForm

    list_display = (
        "id",
        "get_province",
        "aimfacilityname",
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

    list_filter = (DistrictFilter, AimpeeFacilityFilter)
    search_fields = ("aimfacilityname__name", "aimfacilityname__hfcode")

    @admin.display(description="Province")
    def get_province(self, obj):
        return obj.aimfacilityname.districtfk.provincefk.name

    def province_filter_kwargs(self, request):
        return {"aimfacilityname__districtfk__provincefk": user_province(request)}

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "aimfacilityname" and not request.user.is_superuser:
            prov = user_province(request)
            kwargs["queryset"] = Facility.objects.filter(districtfk__provincefk=prov) if prov else Facility.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

# ============================================================
# AIM-PPH
# ============================================================
@admin.register(aimpph)
class AimpphAdmin(ProvinceRestrictedAdminMixin, admin.ModelAdmin):
    form = AimpphAdminForm

    list_display = (
        "id",
        "get_province",
        "aimfacilityname",
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

    list_filter = (DistrictFilter, AimpeeFacilityFilter)
    search_fields = ("aimfacilityname__name", "aimfacilityname__hfcode")

    @admin.display(description="Province")
    def get_province(self, obj):
        return obj.aimfacilityname.districtfk.provincefk.name

    def province_filter_kwargs(self, request):
        return {"aimfacilityname__districtfk__provincefk": user_province(request)}

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "aimfacilityname" and not request.user.is_superuser:
            prov = user_province(request)
            kwargs["queryset"] = Facility.objects.filter(districtfk__provincefk=prov) if prov else Facility.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(WhoChildbirthChecklistMonthly)
class WhoChildbirthChecklistMonthlyAdmin(ProvinceRestrictedAdminMixin, admin.ModelAdmin):

    """
    Same admin logic pattern as your SafeSurgery admin:
    - province-restricted facility dropdown
    - list_display includes key ratios
    - save_model computes ratios (stored fields OR assigns to attrs if you later add DB fields)
    """

    # If you have a dedicated form, use it here
    # form = WhoChildbirthChecklistMonthlyAdminForm

    list_display = (
        "id",
        "get_province",
        "facility_name",
        "shamsi_year",
        "shamsi_month",
        "period",
        "total_deliveries",
        "files_selected",
        "sec1_complete",
        "sec1_completeness_ratio",
        "cervix_ge4_admission",
        "partograph_started_ge4",
        "partograph_use_ge4_rate",
        "sec2_complete",
        "sec2_completeness_ratio",
        "newborn_supplies_5_available",
        "newborn_supplies_5_ratio",
        "sec3_complete",
        "sec3_completeness_ratio",
        "bf_s2s_first_hour",
        "bf_s2s_first_hour_ratio",
        "sec4_complete",
        "sec4_completeness_ratio",
        "abx_need_checked_newborn",
        "abx_need_checked_ratio",
        "all4_sections_complete",
        "all4_sections_completeness_ratio",
    )

    # NOTE:
    # In your model I provided ratios as @property. Those are already "read-only".
    # Adding them here just makes them show in the form "as read-only fields"
    readonly_fields = (
        "sec1_completeness_ratio",
        "partograph_use_ge4_rate",
        "sec2_completeness_ratio",
        "newborn_supplies_5_ratio",
        "sec3_completeness_ratio",
        "bf_s2s_first_hour_ratio",
        "sec4_completeness_ratio",
        "abx_need_checked_ratio",
        "all4_sections_completeness_ratio",
        "created_at",
        "updated_at",
    )

    # Keep your existing filters pattern (replace if you have a different facility filter)
    #list_filter = (DistrictFilter, AimpeeFacilityFilter)
    search_fields = ("facility_name",)

    # -------------------------
    # Shared percent helper
    # -------------------------
    def _pct(self, num, den):
        try:
            if num is None or den in (None, 0):
                return None
            return (Decimal(num) / Decimal(den)) * Decimal("100.0")
        except (InvalidOperation, ZeroDivisionError):
            return None

    # ----------------------------------------------------
    # OPTIONAL: compute & attach stored ratios on save
    # ----------------------------------------------------
    def save_model(self, request, obj, form, change):
        """
        Your current model uses @property ratios (calculated, not stored).
        This save_model keeps the SAME admin "logic style" you showed:
        - calculates ratios safely
        - if later you add DB fields, the assignments will start persisting automatically.
        """
        # These setattr() will not persist unless you add matching model fields.
        setattr(obj, "sec1_completeness_ratio_calc", self._pct(obj.sec1_complete, obj.files_selected))
        setattr(obj, "sec2_completeness_ratio_calc", self._pct(obj.sec2_complete, obj.files_selected))
        setattr(obj, "sec3_completeness_ratio_calc", self._pct(obj.sec3_complete, obj.files_selected))
        setattr(obj, "sec4_completeness_ratio_calc", self._pct(obj.sec4_complete, obj.files_selected))

        setattr(obj, "partograph_use_ge4_rate_calc", self._pct(obj.partograph_started_ge4, obj.cervix_ge4_admission))
        setattr(obj, "newborn_supplies_5_ratio_calc", self._pct(obj.newborn_supplies_5_available, obj.total_deliveries))
        setattr(obj, "bf_s2s_first_hour_ratio_calc", self._pct(obj.bf_s2s_first_hour, obj.total_deliveries))
        setattr(obj, "abx_need_checked_ratio_calc", self._pct(obj.abx_need_checked_newborn, obj.total_deliveries))
        setattr(obj, "all4_sections_completeness_ratio_calc", self._pct(obj.all4_sections_complete, obj.files_selected))

        super().save_model(request, obj, form, change)

    # -------------------------
    # Province display + rules
    # -------------------------
    @admin.display(description="Province")
    def get_province(self, obj):
        """
        If you change facility_name to a FK (recommended), then replace this with:
        return obj.facility.districtfk.provincefk.name
        """
        # If facility_name is just text, province cannot be derived.
        # Return "-" to avoid crashing admin.
        return "-"

    def province_filter_kwargs(self, request):
        """
        If you change facility_name to a FK, update filter kwargs accordingly.
        """
        # Example (when you change to facility FK):
        # return {"facility__districtfk__provincefk": user_province(request)}
        return {}

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Only applies if you replace facility_name with a FK field like 'facility'.
        Keep the same logic style as your SafeSurgery admin.
        """
        # Example (when you change to facility FK):
        # if db_field.name == "facility" and not request.user.is_superuser:
        #     prov = user_province(request)
        #     kwargs["queryset"] = (
        #         Facility.objects.filter(districtfk__provincefk=prov) if prov else Facility.objects.none()
        #     )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    # -------------------------
    # Extra guard in admin UI
    # -------------------------
    def save_related(self, request, form, formsets, change):
        """
        Ensures model.clean() errors show nicely in admin.
        """
        obj = form.instance
        try:
            obj.full_clean()
        except ValidationError as e:
            form.add_error(None, e)
            return
        super().save_related(request, form, formsets, change)

# ============================================================
# Safe Surgery (C-Section clinical)
# ============================================================
@admin.register(safesurgeryclinical)
class CSectionSafeSurgeryAdmin(ProvinceRestrictedAdminMixin, admin.ModelAdmin):
    form = AimpeeAdminForm  # if you really intended this, keep; otherwise replace with correct form

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

    list_filter = (DistrictFilter, AimpeeFacilityFilter)
    search_fields = ("aimfacilityname__name", "aimfacilityname__hfcode")

    def _pct(self, num, den):
        try:
            if num is None or den in (None, 0):
                return None
            return (Decimal(num) / Decimal(den)) * Decimal("100.0")
        except (InvalidOperation, ZeroDivisionError):
            return None

    def save_model(self, request, obj, form, change):
        obj.cs_rate = self._pct(obj.total_cs, obj.total_deliv)
        obj.who_ssc_rate = self._pct(obj.who_ssc_completed, obj.total_cs)
        obj.safe_tracker_rate = self._pct(obj.safe_tracker_complete, obj.total_cs)
        obj.pph_cs_rate = self._pct(obj.pph_cs_num, obj.total_cs)
        obj.qbl_cs_rate = self._pct(obj.qbl_cs_num, obj.total_cs)
        obj.postop_fever_rate = self._pct(obj.postop_fever_num, obj.total_cs)
        obj.bladder_injury_rate = self._pct(obj.bladder_injury_num, obj.total_cs)
        obj.bowel_injury_rate = self._pct(obj.bowel_injury_num, obj.total_cs)
        obj.hyst_rate = self._pct(obj.hyst_num, obj.total_cs)
        obj.vag_clean_rate = self._pct(obj.vag_clean_num, obj.total_cs)
        obj.foley_after_anes_rate = self._pct(obj.foley_after_anes_num, obj.total_cs)
        obj.abx_proph_rate = self._pct(obj.abx_proph_num, obj.total_cs)
        obj.skin_prep_rate = self._pct(obj.skin_prep_num, obj.total_cs)
        super().save_model(request, obj, form, change)

    @admin.display(description="Province")
    def get_province(self, obj):
        return obj.aimfacilityname.districtfk.provincefk.name

    def province_filter_kwargs(self, request):
        return {"aimfacilityname__districtfk__provincefk": user_province(request)}

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "aimfacilityname" and not request.user.is_superuser:
            prov = user_province(request)
            kwargs["queryset"] = Facility.objects.filter(districtfk__provincefk=prov) if prov else Facility.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

# ============================================================
# Facility Admin
# ============================================================

@admin.register(Facility)
class FacilityAdmin(ProvinceRestrictedAdminMixin, admin.ModelAdmin):
    list_display = [
        "id", "get_province", "districtfk", "name", "hfcode",
        "facilitytypefk", "skilllab", "aim", "aimphase", "safesurgery",
        "ganc", "afiat", "nbcc", "sncu", "kmc",
    ]
    list_filter = ["districtfk__provincefk", "facilitytypefk"]
    search_fields = ["name", "districtfk__name", "districtfk__provincefk__name"]
    list_per_page = 15

    def province_filter_kwargs(self, request):
        return {"districtfk__provincefk": user_province(request)}

    @admin.display(description="Province")
    def get_province(self, obj):
        return obj.districtfk.provincefk.name


# ============================================================
# HQIP INLINE (details lines)
# ============================================================
class AssessmentLineInline(admin.TabularInline):
    model = HQIPAssessment
    extra = 0
    can_delete = False
    show_change_link = False

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

        if request.user.is_superuser:
            return qs

        prov = user_province(request)
        if prov is None:
            return qs.none()
        return qs.filter(header__facilityfk__districtfk__provincefk=prov)

    @admin.display(description="Section")
    def get_section(self, obj):
        return obj.criteriafk.standardfk.sectionfk.name if obj.criteriafk_id else "-"

    @admin.display(description="Standard")
    def get_standard(self, obj):
        return obj.criteriafk.standardfk.name if obj.criteriafk_id else "-"

    @admin.display(description="Criteria")
    def get_criteria(self, obj):
        return obj.criteriafk.name if obj.criteriafk_id else "-"

    def has_add_permission(self, request, obj=None):
        return False

# Score PK mapping:
SCORE_YES_ID = 1
SCORE_NO_ID = 2
SCORE_NA_ID = 3

# ============================================================
# HQIP HEADER ADMIN (creates details lines)
# ============================================================
@admin.register(HQIPAssessmentHeader)
class AssessmentHeaderAdmin(ProvinceRestrictedAdminMixin, admin.ModelAdmin):
    inlines = [AssessmentLineInline]

    list_display = (
        "facilityfk",
        "assessmenttype",
        "assessmentdate",
        "areafk",
        "assesorfk",
        "hqip_dashboard_button",
        "hqip_facility_button",
        "hqip_rca_button",
        "hqip_priority_button",
        "created_at",
        "id",
    )

    list_filter = (HQIPProvinceFilter, "areafk")
    search_fields = ("facilityfk__name", "facilityfk__hfcode")
    list_per_page = 10

    # ---------------------------
    # Province restriction (mix-in requirement)
    # ---------------------------
    def province_filter_kwargs(self, request):
        return {"facilityfk__districtfk__provincefk": user_province(request)}

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "facilityfk" and not request.user.is_superuser:
            prov = user_province(request)
            if prov:
                kwargs["queryset"] = Facility.objects.filter(districtfk__provincefk=prov).order_by("name")
            else:
                kwargs["queryset"] = Facility.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    # ---- helpers ----
    def _round2(self, x):
        if x is None:
            return None
        return float(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    def _pct(self, yes_count, applicable_count):
        if not applicable_count:
            return None
        return self._round2((Decimal(yes_count) / Decimal(applicable_count)) * Decimal(100))

    # ---- create missing detail lines AFTER header save ----
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            if hasattr(obj, "created_by"):
                obj.created_by = request.user
            if hasattr(obj, "created_at"):
                obj.created_at = timezone.now()
        else:
            if hasattr(obj, "updated_by"):
                obj.updated_by = request.user
            if hasattr(obj, "updated_at"):
                obj.updated_at = timezone.now()

        super().save_model(request, obj, form, change)

        # Create all criteria lines for selected Area
        criteria_qs = Criteria.objects.filter(
            standardfk__sectionfk__areafk=obj.areafk
        ).order_by(
            "standardfk__sectionfk__id",
            "standardfk__id",
            "id",
        )

        existing_ids = set(obj.lines.values_list("criteriafk_id", flat=True))
        to_create = [
            HQIPAssessment(header=obj, criteriafk=c, scorefk=None)
            for c in criteria_qs
            if c.id not in existing_ids
        ]

        if to_create:
            with transaction.atomic():
                HQIPAssessment.objects.bulk_create(to_create)

    # ---- admin dashboards urls ----
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
            path(
                "hqip-rca-dashboard/",
                self.admin_site.admin_view(self.hqip_rca_dashboard),
                name="hqip_rca_dashboard",
            ),
            path(
                "hqip-priority-areas/",
                self.admin_site.admin_view(self.hqip_priority_areas),
                name="hqip_priority_areas",
            ),
        ]
        return custom_urls + urls

    # ---- buttons ----
    @admin.display(description="Score")
    def hqip_dashboard_button(self, obj):
        base_url = reverse("admin:hqip_standards_dashboard")
        qs = urlencode({"header_id": obj.id})
        return format_html('<a class="button" href="{}?{}">Score</a>', base_url, qs)

    @admin.display(description="Detail")
    def hqip_facility_button(self, obj):
        base_url = reverse("admin:hqip_facility_dashboard")
        qs = urlencode({"facility": obj.facilityfk_id, "header_id": obj.id})
        return format_html('<a class="button" href="{}?{}">View</a>', base_url, qs)

    @admin.display(description="RCA")
    def hqip_rca_button(self, obj):
        base_url = reverse("admin:hqip_rca_dashboard")
        qs = urlencode({"header_id": obj.id})
        return format_html('<a class="button" href="{}?{}">RCA</a>', base_url, qs)

    @admin.display(description="Priority")
    def hqip_priority_button(self, obj):
        base_url = reverse("admin:hqip_priority_areas")
        qs = urlencode({"facility_id": obj.facilityfk_id})
        return format_html('<a class="button" href="{}?{}">Priority</a>', base_url, qs)

    def _compute_hqip_rollups(self, headers_qs):
        """
        Shared HQIP rollup calculator:
        Criteria -> Standard %  (YES / (YES+NO)) ignoring NA/NULL
        Section % = average(Standard %)
        Area %    = average(Section %)

        Returns:
        standard_results: list[dict]
        section_results:  list[dict]
        area_results:     list[dict]
        """

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

        from collections import defaultdict

        standard_results = []
        section_results = []
        area_results = []

        section_to_standard_percents = defaultdict(list)
        area_to_section_percents = defaultdict(list)

        # name maps
        sec_name_map = {}
        area_name_map = {}

        # ---------- Standard level ----------
        for r in std_rows:
            area_id = r["criteriafk__standardfk__sectionfk__areafk__id"]
            sec_id = r["criteriafk__standardfk__sectionfk__id"]
            sec_key = (area_id, sec_id)

            area_name = r["criteriafk__standardfk__sectionfk__areafk__name"] or "-"
            sec_name = r["criteriafk__standardfk__sectionfk__name"] or "-"
            std_name = r["criteriafk__standardfk__name"] or "-"

            sec_name_map[sec_key] = (area_name, sec_name)
            area_name_map[area_id] = area_name

            den = r["applicable"]
            num = r["yes"]
            std_percent = self._pct(num, den)  # <- YOUR SAME helper (YES/(YES+NO))*100

            standard_results.append({
                "area": area_name,
                "section": sec_name,
                "standard": std_name,
                "yes": num,
                "applicable": den,
                "percent": std_percent,
            })

            if std_percent is not None:
                section_to_standard_percents[sec_key].append(std_percent)

        # ---------- Section level = average(Standard %) ----------
        for sec_key, percents in section_to_standard_percents.items():
            area_id, _sec_id = sec_key
            area_name, sec_name = sec_name_map.get(sec_key, ("-", "-"))

            sec_percent = self._round2(sum(percents) / len(percents)) if percents else None

            section_results.append({
                "area": area_name,
                "section": sec_name,
                "num_standards_used": len(percents),
                "percent": sec_percent,
            })

            if sec_percent is not None:
                area_to_section_percents[area_id].append(sec_percent)

        section_results.sort(key=lambda x: (x["area"], x["section"]))

        # ---------- Area level = average(Section %) ----------
        for area_id, percents in area_to_section_percents.items():
            area_percent = self._round2(sum(percents) / len(percents)) if percents else None
            area_results.append({
                "area": area_name_map.get(area_id, "-"),
                "num_sections_used": len(percents),
                "percent": area_percent,
            })

        area_results.sort(key=lambda x: x["area"])

        return standard_results, section_results, area_results

    # ==========================================================
    # A) STANDARDS DASHBOARD
    # ==========================================================
    def hqip_standards_dashboard(self, request):
        header_id = request.GET.get("header_id")
        headers_qs = self.get_queryset(request)

        standard_results, section_results, area_results = self._compute_hqip_rollups(headers_qs)

        header_obj = None
        error_message = None

        # Row-level: lock to exact header
        if header_id:
            headers_qs = headers_qs.filter(id=header_id).select_related(
                "facilityfk__districtfk__provincefk", "areafk", "assessmenttype"
            )
            header_obj = headers_qs.first()
            selected_province = None  # irrelevant when header_id is set

            if not header_obj:
                error_message = "No header selected (missing header_id) or you don’t have access to that header."
                headers_qs = headers_qs.none()
        else:
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
        area_to_section_percents = defaultdict(list)
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

        section_results = []
        for sec_key, percents in section_to_standard_percents.items():
            area_id, _sec_id = sec_key
            area_name, sec_name = sec_name_map.get(sec_key, ("-", "-"))
            sec_percent = self._round2(sum(percents) / len(percents)) if percents else None

            section_results.append({
                "area": area_name,
                "section": sec_name,
                "num_standards_used": len(percents),
                "percent": sec_percent,
            })

            if sec_percent is not None:
                area_to_section_percents[area_id].append(sec_percent)

        section_results.sort(key=lambda x: (x["area"], x["section"]))

        area_results = []
        for area_id, percents in area_to_section_percents.items():
            area_percent = self._round2(sum(percents) / len(percents)) if percents else None
            area_results.append({
                "area": area_name_map.get(area_id, "-"),
                "num_sections_used": len(percents),
                "percent": area_percent,
            })
        area_results.sort(key=lambda x: x["area"])

        # show province dropdown only in global mode (no header_id)
        provinces = Province.objects.all().order_by("name") if (request.user.is_superuser and not header_id) else None

        context = dict(
            self.admin_site.each_context(request),
            title="HQIP Dashboard",
            header_obj=header_obj,              # ✅ add
            error_message=error_message,        # ✅ add
            standard_results=standard_results,
            section_results=section_results,
            area_results=area_results,
            provinces=provinces,
            selected_province=selected_province,
            header_id=header_id,
        )
        return TemplateResponse(request, "admin/hiva/hqip_dashboard_full.html", context)

    # ==========================================================
    # B) FACILITY DRILL-DOWN DASHBOARD
    # ==========================================================
    def hqip_facility_dashboard(self, request):
        selected_province = request.GET.get("province")
        selected_facility = request.GET.get("facility")
        selected_area = request.GET.get("area")
        selected_type = request.GET.get("assessmenttype")
        date_from = request.GET.get("date_from")
        date_to = request.GET.get("date_to")
        header_id = request.GET.get("header_id")

        facilities_qs = Facility.objects.all().select_related("districtfk__provincefk")

        if not request.user.is_superuser:
            prov = user_province(request)
            facilities_qs = facilities_qs.filter(districtfk__provincefk=prov) if prov else Facility.objects.none()
        if request.user.is_superuser and selected_province:
            facilities_qs = facilities_qs.filter(districtfk__provincefk_id=selected_province)

        facilities = facilities_qs.order_by("name")
        areas = Area.objects.all().order_by("name")
        types = Assessmenttype.objects.all().order_by("name")
        provinces = Province.objects.all().order_by("name") if request.user.is_superuser else None

        facility_obj = None
        header_list = []
        standard_results, section_results, area_results = [], [], []
        std_chart_json, sec_chart_json = [], []
        error_message = None

        # If header_id is present, force facility from that header (prevents mismatch)
        header_obj = None
        if header_id:
            header_obj = self.get_queryset(request).filter(id=header_id).select_related(
                "facilityfk__districtfk__provincefk", "areafk", "assessmenttype"
            ).first()
            if not header_obj:
                error_message = "No header selected (missing header_id) or you don’t have access to that header."
            else:
                facility_obj = header_obj.facilityfk
                selected_facility = str(facility_obj.id)

        # Normal mode: use selected facility
        if (not facility_obj) and selected_facility:
            facility_obj = Facility.objects.filter(pk=selected_facility).select_related("districtfk__provincefk").first()
            if facility_obj and (not request.user.is_superuser):
                prov = user_province(request)
                if not prov or facility_obj.districtfk.provincefk_id != prov.id:
                    facility_obj = None
                    error_message = "You don’t have access to this facility."

        if facility_obj and not error_message:
            headers_qs = self.get_queryset(request).filter(facilityfk=facility_obj)

            # Row lock
            if header_id:
                headers_qs = headers_qs.filter(id=header_id)
            else:
                # Optional filters only in global mode
                if selected_area:
                    headers_qs = headers_qs.filter(areafk_id=selected_area)
                if selected_type:
                    headers_qs = headers_qs.filter(assessmenttype_id=selected_type)
                if date_from:
                    headers_qs = headers_qs.filter(assessmentdate__gte=date_from)
                if date_to:
                    headers_qs = headers_qs.filter(assessmentdate__lte=date_to)

            header_list = list(headers_qs.values("id", "assessmentdate"))

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

            for r in std_rows:
                area_name = r["criteriafk__standardfk__sectionfk__areafk__name"] or "-"
                sec_name = r["criteriafk__standardfk__sectionfk__name"] or "-"
                std_name = r["criteriafk__standardfk__name"] or "-"

                area_id = r["criteriafk__standardfk__sectionfk__areafk__id"]
                sec_id = r["criteriafk__standardfk__sectionfk__id"]
                sec_key = (area_id, sec_id)

                sec_name_map[sec_key] = (area_name, sec_name)
                area_name_map[area_id] = area_name

                den = r["applicable"]
                num = r["yes"]
                std_percent = self._pct(num, den)

                standard_results.append({
                    "area": area_name,
                    "section": sec_name,
                    "standard": std_name,
                    "yes": num,
                    "applicable": den,
                    "percent": std_percent,
                })

                if std_percent is not None:
                    section_to_standard_percents[sec_key].append(std_percent)

            for sec_key, percents in section_to_standard_percents.items():
                area_id, _sec_id = sec_key
                area_name, sec_name = sec_name_map.get(sec_key, ("-", "-"))
                sec_percent = self._round2(sum(percents) / len(percents)) if percents else None

                section_results.append({
                    "area": area_name,
                    "section": sec_name,
                    "num_standards_used": len(percents),
                    "percent": sec_percent,
                })

                if sec_percent is not None:
                    area_to_section_percents[area_id].append(sec_percent)

            section_results.sort(key=lambda x: (x["area"], x["section"]))

            for area_id, percents in area_to_section_percents.items():
                area_percent = self._round2(sum(percents) / len(percents)) if percents else None
                area_results.append({
                    "area": area_name_map.get(area_id, "-"),
                    "num_sections_used": len(percents),
                    "percent": area_percent,
                })
            area_results.sort(key=lambda x: x["area"])

            std_chart_json = [{"label": r["standard"], "value": r["percent"]} for r in standard_results if r.get("percent") is not None]
            sec_chart_json = [{"label": r["section"], "value": r["percent"]} for r in section_results if r.get("percent") is not None]

        context = dict(
            self.admin_site.each_context(request),
            title="HQIP Facility Drill-Down",
            error_message=error_message,     # ✅ add
            header_obj=header_obj,           # ✅ add
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
            header_id=header_id,
            header_list=header_list,
            standard_results=standard_results,
            section_results=section_results,
            area_results=area_results,
            std_chart_json=std_chart_json,
            sec_chart_json=sec_chart_json,
        )
        return TemplateResponse(request, "admin/hiva/hqip_facility_dashboard.html", context)

    # ==========================================================
    # C) RCA DASHBOARD (row-level only)
    # ==========================================================
    def hqip_rca_dashboard(self, request):
        header_id = request.GET.get("header_id")
        headers_qs = self.get_queryset(request)

        error_message = None

        if not header_id:
            error_message = "No header selected (missing header_id) or you don’t have access to that header."
            context = dict(
                self.admin_site.each_context(request),
                title="HQIP RCA – Failed Criteria (NO only)",
                header_obj=None,
                rca_rows=[],
                error_message=error_message,  # ✅ add
            )
            return TemplateResponse(request, "admin/hiva/hqip_rca_dashboard.html", context)

        header_obj = (
            headers_qs
            .filter(id=header_id)
            .select_related("facilityfk__districtfk__provincefk", "areafk", "assessmenttype")
            .first()
        )

        if not header_obj:
            error_message = "No header selected (missing header_id) or you don’t have access to that header."
            context = dict(
                self.admin_site.each_context(request),
                title="HQIP RCA – Failed Criteria (NO only)",
                header_obj=None,
                rca_rows=[],
                error_message=error_message,  # ✅ add
            )
            return TemplateResponse(request, "admin/hiva/hqip_rca_dashboard.html", context)

        rca_rows = (
            HQIPAssessment.objects
            .filter(header_id=header_obj.id, scorefk_id=SCORE_NO_ID)
            .select_related(
                "criteriafk",
                "criteriafk__standardfk",
                "criteriafk__standardfk__sectionfk",
                "criteriafk__standardfk__sectionfk__areafk",
                "header",
                "header__facilityfk",
            )
            .order_by(
                "criteriafk__standardfk__sectionfk__areafk__name",
                "criteriafk__standardfk__sectionfk__name",
                "criteriafk__standardfk__name",
                "criteriafk__id",
            )
        )

        context = dict(
            self.admin_site.each_context(request),
            title="HQIP RCA – Failed Criteria (NO only)",
            header_obj=header_obj,
            rca_rows=rca_rows,
            error_message=None,
        )
        return TemplateResponse(request, "admin/hiva/hqip_rca_dashboard.html", context)

    def hqip_priority_areas(self, request):
        """
        Priority thematic areas for a FACILITY:
        - Uses the SAME % calculations as Score/View (via _compute_hqip_rollups)
        - Flags lowest 3 thematic areas as Priority
        - Optional export: ?facility_id=107&export=1
        """

        facility_id = request.GET.get("facility_id")
        export = request.GET.get("export") == "1"

        # Province-restricted headers (superuser sees all)
        headers_base = self.get_queryset(request)

        facility_obj = None
        rows = []
        error_message = None

        if not facility_id:
            error_message = "No facility selected."
            context = dict(
                self.admin_site.each_context(request),
                title="HQIP Priority Thematic Areas",
                error_message=error_message,
                facility_obj=None,
                rows=[],
            )
            return TemplateResponse(request, "admin/hiva/hqip_priority_areas.html", context)

        # Load facility (and enforce access)
        facility_obj = Facility.objects.select_related("districtfk__provincefk").filter(pk=facility_id).first()
        if not facility_obj:
            error_message = "Invalid facility."
            context = dict(
                self.admin_site.each_context(request),
                title="HQIP Priority Thematic Areas",
                error_message=error_message,
                facility_obj=None,
                rows=[],
            )
            return TemplateResponse(request, "admin/hiva/hqip_priority_areas.html", context)

        if not request.user.is_superuser:
            prov = user_province(request)
            if not prov or facility_obj.districtfk.provincefk_id != prov.id:
                error_message = "You don’t have access to this facility."
                context = dict(
                    self.admin_site.each_context(request),
                    title="HQIP Priority Thematic Areas",
                    error_message=error_message,
                    facility_obj=None,
                    rows=[],
                )
                return TemplateResponse(request, "admin/hiva/hqip_priority_areas.html", context)

        # Only headers for this facility
        headers_qs = headers_base.filter(facilityfk_id=facility_obj.id)

        # If no headers, show empty
        if not headers_qs.exists():
            error_message = "No HQIP assessments found for this facility."
            context = dict(
                self.admin_site.each_context(request),
                title="HQIP Priority Thematic Areas",
                error_message=error_message,
                facility_obj=facility_obj,
                rows=[],
            )
            return TemplateResponse(request, "admin/hiva/hqip_priority_areas.html", context)

        # ---- SAME calculations as Score/View ----
        _std, _sec, area_results = self._compute_hqip_rollups(headers_qs)

        # For display ONLY (not used in %): raw counts per area
        raw_counts = (
            HQIPAssessment.objects
            .filter(header__in=headers_qs)
            .values("criteriafk__standardfk__sectionfk__areafk__name")
            .annotate(
                yes=Count("id", filter=Q(scorefk_id=SCORE_YES_ID)),
                applicable=Count("id", filter=Q(scorefk_id__in=[SCORE_YES_ID, SCORE_NO_ID])),
            )
        )
        raw_map = {
            r["criteriafk__standardfk__sectionfk__areafk__name"] or "-": {
                "yes": r["yes"],
                "applicable": r["applicable"],
            }
            for r in raw_counts
        }

        # Build rows: percent comes from area_results (HQIP hierarchy)
        rows = []
        for r in area_results:
            area_name = r["area"]
            rows.append({
                "area": area_name,
                "percent": r["percent"],
                "num_sections_used": r["num_sections_used"],
                "yes": raw_map.get(area_name, {}).get("yes", 0),
                "applicable": raw_map.get(area_name, {}).get("applicable", 0),
                "is_priority": False,  # set below
            })

        # Priority = lowest 3 by percent (ignore None)
        scored = [x for x in rows if x["percent"] is not None]
        scored_sorted = sorted(scored, key=lambda x: x["percent"])  # lowest first
        priority_set = set([x["area"] for x in scored_sorted[:3]])

        for x in rows:
            x["is_priority"] = (x["area"] in priority_set)

        # Optional: export to Excel
        if export:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Priority Areas"

            ws.append([
                "Facility", "Province", "District", "HF Code",
                "Thematic Area", "HQIP % (Area)", "Priority",
                "YES (criteria)", "Applicable (criteria)", "# Sections used"
            ])

            for x in rows:
                ws.append([
                    facility_obj.name,
                    facility_obj.districtfk.provincefk.name,
                    facility_obj.districtfk.name,
                    facility_obj.hfcode,
                    x["area"],
                    x["percent"] if x["percent"] is not None else "",
                    "PRIORITY" if x["is_priority"] else "NON-PRIORITY",
                    x["yes"],
                    x["applicable"],
                    x["num_sections_used"],
                ])

            resp = HttpResponse(
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            filename = f"HQIP_Priority_Areas_Facility_{facility_obj.id}.xlsx"
            resp["Content-Disposition"] = f'attachment; filename="{filename}"'
            wb.save(resp)
            return resp

        context = dict(
            self.admin_site.each_context(request),
            title="HQIP Priority Thematic Areas",
            error_message=error_message,
            facility_obj=facility_obj,
            rows=rows,
        )
        return TemplateResponse(request, "admin/hiva/hqip_priority_areas.html", context)

# ===========================================================
# Hide HQIPAssessment from admin menu (inline only)
# ============================================================
class HQIPAssessmentAdmin(admin.ModelAdmin):
    list_display = ("id", "header", "criteriafk", "scorefk")

    def has_module_permission(self, request):
        return False  # hide from sidebar

# ============================================================
# Other Admins (keep simple / safe)
# ============================================================
class QICMonthFilter(admin.SimpleListFilter):
    title = _('QI Committee Date (Month + Year)')
    parameter_name = 'qic_month'

    def lookups(self, request, model_admin):
        dates = (Qicdataset.objects.exclude(qiccommdate__isnull=True).dates('qiccommdate', 'month'))
        return [(d.strftime("%Y-%m"), d.strftime("%B %Y")) for d in dates]

    def queryset(self, request, queryset):
        if self.value():
            year, month = self.value().split('-')
            return queryset.filter(qiccommdate__year=year, qiccommdate__month=month)
        return queryset

@admin.register(Qicdataset)
class MyModelqicdataset(admin.ModelAdmin):
    list_display = [
        "id", "qiccommdate", "qicfacility", "qicdatacollector", "qicimplementor",
        "qictoravailvalue", "qiclastmonthvalue", "qicmmavialvalue", "qicmmsignedvalue",
        "qicmmdatausevalue", "qichqiptollavailvalue", "qicpipavailvalue", "qicpipupdatedvalue",
        "qicngoinvolvedvalue", "qicpeertopeeravailvalue", "qicmenteelogbookavialvalue",
        "qicmenteelogbookupdatedvalue", "qicmetwithhealthshuravalue",
        "qichealthshurainvolvedincorractvalue", "qictotalquestions", "image",
    ]
    list_filter = ["qicfacility", QICMonthFilter, "qicfacility__districtfk__provincefk"]
    list_per_page = 20

class Trainingdetails(admin.StackedInline):
    model = Training
    extra = 1

@admin.register(Trainingheader)
class TrainingAdmin(admin.ModelAdmin):
    inlines = [Trainingdetails]
    list_display = (
        "trainingname", "trainingvenue", "trainingstartdate", "trainingenddate",
        "remarks", "expectednumberofparticipant", "traingfocalpoint"
    )
    search_fields = ("trainingname",)

class MpdsrProvinceFilter(ProvinceFromFacilityFilter):
    province_path = "facilityname__districtfk__provincefk"

@admin.register(Mpdsr)
class mpdsrshow(ProvinceRestrictedAdminMixin, admin.ModelAdmin):
    list_display = [
        "id", "yearmpdsr", "monthmpdsr", "facilityname",
        "n_mpdsrcommittee", "n_maternaldeathreported", "n_maternaldeathreviewed",
        "causeofmaternaldeaths_m", "nastillbirthreportedreported",
        "nastillbirthreportedreviewed", "nistillbirthreported", "nistillbirthreviewed",
        "nndeath_afteralivebirth_reported", "nndeath_afteralivebirth_reviewed",
    ]
    list_filter = [MpdsrProvinceFilter, "monthmpdsr"]
    search_fields = ("facilityname__name", "facilityname__districtfk__name", "facilityname__districtfk__provincefk__name")

    def province_filter_kwargs(self, request):
        return {"facilityname__districtfk__provincefk": user_province(request)}

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "facilityname" and not request.user.is_superuser:
            prov = user_province(request)
            kwargs["queryset"] = Facility.objects.filter(districtfk__provincefk=prov) if prov else Facility.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

# ============================================================
# User admin with Profile inline
# ============================================================
User = get_user_model()

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    fk_name = "user"
    can_delete = False
    extra = 0
    max_num = 1

class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)

admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# ============================================================
# Register remaining simple models
# ============================================================
admin.site.register(Score)
admin.site.register(Criteria)
admin.site.register(Section)
admin.site.register(Standards)
admin.site.register(Area)
admin.site.register(Assessmenttype)
admin.site.register(Province)
admin.site.register(District)
admin.site.register(Facilitytype)
admin.site.register(Implementor)
admin.site.register(Assessor)
admin.site.register(Participationtype)
admin.site.register(Participantposition)
admin.site.register(Participanteducation)
admin.site.register(Position)
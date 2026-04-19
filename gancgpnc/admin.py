from django.contrib import admin
from .models import (
    Gancohort,
    Gancenrollment,
    Gancfirstsession,
    Gancsecondsession,
    Gancthirdsession,
    Gancfouthsession,
    Gancdelivery,
    GroupPncfirstSession,
    GroupPncsecondSession,
)

# import Facility from hiva
from hiva.models import Facility


# ============================================================
# Province helper (same style as hiva admin.py)
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
# Optional reusable province filters
# ============================================================

class GancCohortProvinceFilter(admin.SimpleListFilter):
    title = "Province"
    parameter_name = "province"

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        rows = qs.values_list(
            "facility__districtfk__provincefk__id",
            "facility__districtfk__provincefk__name",
        ).distinct().order_by("facility__districtfk__provincefk__name")
        return [(pid, pname) for pid, pname in rows if pid]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(facility__districtfk__provincefk_id=self.value())
        return queryset


class EnrollmentProvinceFilter(admin.SimpleListFilter):
    title = "Province"
    parameter_name = "province"

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        rows = qs.values_list(
            "cohortname__facility__districtfk__provincefk__id",
            "cohortname__facility__districtfk__provincefk__name",
        ).distinct().order_by("cohortname__facility__districtfk__provincefk__name")
        return [(pid, pname) for pid, pname in rows if pid]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(cohortname__facility__districtfk__provincefk_id=self.value())
        return queryset


class SessionProvinceFilter(admin.SimpleListFilter):
    title = "Province"
    parameter_name = "province"

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        rows = qs.values_list(
            "registerid__cohortname__facility__districtfk__provincefk__id",
            "registerid__cohortname__facility__districtfk__provincefk__name",
        ).distinct().order_by("registerid__cohortname__facility__districtfk__provincefk__name")
        return [(pid, pname) for pid, pname in rows if pid]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                registerid__cohortname__facility__districtfk__provincefk_id=self.value()
            )
        return queryset

# ============================================================
# GANC Cohort
# ============================================================

@admin.register(Gancohort)
class GancohortAdmin(ProvinceRestrictedAdminMixin, admin.ModelAdmin):
    list_display = (
        "get_province",
        "facility",
        "cohortname",
        "cohortnumber",
        "cohortstatus",
        "cohortchecklist",
        "target_size",
        "created_by",
        "created_at",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    )

    list_filter = (
        GancCohortProvinceFilter,
        "facility",
        "cohortstatus",
    )

    search_fields = (
        "cohortname",
        "facility__name",
        "facility__hfcode",
    )

    list_per_page = 20

    fieldsets = (
        ("Cohort Information", {
            "fields": (
                "facility",
                "cohortname",
                "cohortnumber",
                "cohortstatus",
                "cohortchecklist",
                "target_size",
            )
        }),
        ("Other Information", {
            "fields": (
                "remarks",
            )
        }),
        ("Audit Information", {
            "fields": (
                "created_at",
                "updated_at",
                "created_by",
                "updated_by",
            ),
            "classes": ("collapse",),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description="Province")
    def get_province(self, obj):
        return obj.facility.districtfk.provincefk.name if obj.facility and obj.facility.districtfk else "-"

    def province_filter_kwargs(self, request):
        return {"facility__districtfk__provincefk": user_province(request)}

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "facility" and not request.user.is_superuser:
            prov = user_province(request)
            kwargs["queryset"] = (
                Facility.objects.filter(districtfk__provincefk=prov).order_by("name")
                if prov else Facility.objects.none()
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# ============================================================
# GANC Enrollment
# ============================================================

@admin.register(Gancenrollment)
class GancenrollmentAdmin(ProvinceRestrictedAdminMixin, admin.ModelAdmin):
    list_display = (
        "name",
        "fathername",
        "cohortname",
        "get_facility",
        "get_province",
        "enrollmentid",
        "contactnumber",
        "education_level",
        "gravida",
        "gafirstanc",
        "edd",
        "age_years",
        "transfer_in",
        "numerof_ancvisits",
    )

    list_filter = (
        EnrollmentProvinceFilter,
        "cohortname",
        "edd",
        "education_level",
        "transfer_in",
    )

    search_fields = (
        "name",
        "fathername",
        "contactnumber",
        "address",
        "education_level",
        "cohortname__cohortname",
        "cohortname__facility__name",
        "cohortname__facility__district__name",
        "cohortname__facility__district__province__name",
    )

    list_per_page = 20

    fieldsets = (
        ("Enrollment Information", {
            "fields": (
                "cohortname",
                "enrollmentid",
                "name",
                "fathername",
                "contactnumber",
                "address",
            )
        }),
        ("Pregnancy Information", {
            "fields": (
                "gravida",
                "gafirstanc",
                "edd",
                "age_years",
                "transfer_in",
                "numerof_ancvisits",
            )
        }),
        ("Background Information", {
            "fields": (
                "education_level",
            )
        }),
        ("Other Information", {
            "fields": (
                "remarks",
            )
        }),
    )

    @admin.display(description="Facility")
    def get_facility(self, obj):
        return obj.cohortname.facility.name if obj.cohortname and obj.cohortname.facility else "-"

    @admin.display(description="Province")
    def get_province(self, obj):
        cohort = obj.cohortname
        if cohort and cohort.facility and cohort.facility.districtfk:
            return cohort.facility.districtfk.provincefk.name
        return "-"

    def province_filter_kwargs(self, request):
        return {"cohortname__facility__districtfk__provincefk": user_province(request)}

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "cohortname" and not request.user.is_superuser:
            prov = user_province(request)
            kwargs["queryset"] = (
                Gancohort.objects.filter(facility__districtfk__provincefk=prov).order_by("cohortname")
                if prov else Gancohort.objects.none()
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# ============================================================
# Shared helper for session-like admins
# ============================================================

class BaseSessionAdmin(ProvinceRestrictedAdminMixin, admin.ModelAdmin):
    list_per_page = 20

    def province_filter_kwargs(self, request):
        return {"registerid__cohortname__facility__districtfk__provincefk": user_province(request)}

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "registerid" and not request.user.is_superuser:
            prov = user_province(request)
            kwargs["queryset"] = (
                Gancenrollment.objects.filter(
                    cohortname__facility__districtfk__provincefk=prov
                ).order_by("name")
                if prov else Gancenrollment.objects.none()
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.display(description="Province")
    def get_province(self, obj):
        try:
            return obj.registerid.cohortname.facility.districtfk.provincefk.name
        except Exception:
            return "-"

    @admin.display(description="Facility")
    def get_facility(self, obj):
        try:
            return obj.registerid.cohortname.facility.name
        except Exception:
            return "-"


# ============================================================
# GANC First Session
# ============================================================

@admin.register(Gancfirstsession)
class GancfirstsessionAdmin(BaseSessionAdmin):
    list_display = (
        "registerid",
        "get_facility",
        "get_province",
        "sessiontype",
        "sessionround",
        "sessiondate",
        "attendance",
        "presentga",
        "bp",
        "anemia",
        "dangersign",
    )
    list_filter = (
        SessionProvinceFilter,
        "sessiontype",
        "sessiondate",
        "attendance",
        "dhypertension",
        "anemia",
        "dangersign",
    )
    search_fields = (
        "registerid__name",
        "registerid__fathername",
        "sessiontype",
        "typeofdangersign",
    )
    ordering = ("-sessiondate",)

    fieldsets = (
        ("Session Information", {
            "fields": (
                "registerid",
                "sessiontype",
                "sessionround",
                "sessiondate",
                "attendance",
                "presentga",
            )
        }),
        ("Maternal Assessment", {
            "fields": (
                "bp",
                "dhypertension",
                "rhypertensiontoMD",
                "weight",
                "anemia",
                "ironfolate",
                "ironfolatepluswomen",
                "pcalcium",
                "acalcium",
                "muac",
                "dmam",
                "rmam",
                "dsam",
                "rsam",
            )
        }),
        ("Laboratory and Screening", {
            "fields": (
                "clabexm",
                "hemoglobin",
                "urinexam",
                "rpositivepuriatomd",
                "coughmorethantwoweeks",
                "rcough",
                "ttvaccine",
            )
        }),
        ("Danger Signs", {
            "fields": (
                "dangersign",
                "typeofdangersign",
            )
        }),
        ("Other Information", {
            "fields": ("remarks",)
        }),
    )


# ============================================================
# GANC Second Session
# ============================================================

@admin.register(Gancsecondsession)
class GancsecondsessionAdmin(BaseSessionAdmin):
    list_display = (
        "registerid",
        "get_facility",
        "get_province",
        "sessiontype",
        "sessionround",
        "sessiondate",
        "attendance",
        "presentga",
        "bp",
        "anemia",
        "mebendazole",
        "dangersign",
    )
    list_filter = (
        SessionProvinceFilter,
        "sessiontype",
        "sessiondate",
        "attendance",
        "dhypertension",
        "anemia",
        "dangersign",
    )
    search_fields = (
        "registerid__name",
        "registerid__fathername",
        "sessiontype",
        "typeofdangersign",
    )
    ordering = ("-sessiondate",)

    fieldsets = (
        ("Session Information", {
            "fields": (
                "registerid",
                "sessiontype",
                "sessionround",
                "sessiondate",
                "attendance",
                "presentga",
            )
        }),
        ("Maternal Assessment", {
            "fields": (
                "bp",
                "dhypertension",
                "rhypertensiontoMD",
                "weight",
                "anemia",
                "ironfolate",
                "ironfolatepluswomen",
                "pcalcium",
                "acalcium",
                "mebendazole",
                "muac",
                "dmam",
                "rmam",
                "dsam",
                "rsam",
            )
        }),
        ("Laboratory and Screening", {
            "fields": (
                "urinexam",
                "rpositivepuriatomd",
                "coughmorethantwoweeks",
                "rcough",
                "ttvaccine",
            )
        }),
        ("Danger Signs", {
            "fields": (
                "dangersign",
                "typeofdangersign",
            )
        }),
        ("Other Information", {
            "fields": ("remarks",)
        }),
    )


# ============================================================
# GANC Third Session
# ============================================================

@admin.register(Gancthirdsession)
class GancthirdsessionAdmin(BaseSessionAdmin):
    list_display = (
        "registerid",
        "get_facility",
        "get_province",
        "sessiontype",
        "sessionround",
        "sessiondate",
        "attendance",
        "presentga",
        "bp",
        "anemia",
        "antedepressionscreening",
        "birthplanningcounseling",
    )
    list_filter = (
        SessionProvinceFilter,
        "sessiontype",
        "sessiondate",
        "attendance",
        "dhypertension",
        "anemia",
        "antedepressionscreening",
        "antedepressiondiagnosed",
        "birthplanningcounseling",
    )
    search_fields = (
        "registerid__name",
        "registerid__fathername",
        "sessiontype",
        "typeofdangersign",
    )
    ordering = ("-sessiondate",)

    fieldsets = (
        ("Session Information", {
            "fields": (
                "registerid",
                "sessiontype",
                "sessionround",
                "sessiondate",
                "attendance",
                "presentga",
            )
        }),
        ("Maternal Assessment", {
            "fields": (
                "bp",
                "dhypertension",
                "rhypertensiontoMD",
                "weight",
                "anemia",
                "ironfolate",
                "ironfolatepluswomen",
                "pcalcium",
                "acalcium",
                "muac",
                "dmam",
                "rmam",
                "dsam",
                "rsam",
            )
        }),
        ("Mental Health", {
            "fields": (
                "antedepressionscreening",
                "antedepressiondiagnosed",
                "rpsychosocialcounselor",
            )
        }),
        ("Laboratory and Screening", {
            "fields": (
                "urinexam",
                "rpositivepuriatomd",
                "coughmorethantwoweeks",
                "rcough",
                "ttvaccine",
            )
        }),
        ("Danger Signs and Counseling", {
            "fields": (
                "dangersign",
                "typeofdangersign",
                "birthplanningcounseling",
            )
        }),
        ("Other Information", {
            "fields": ("remarks",)
        }),
    )


# ============================================================
# GANC Fourth Session
# ============================================================

@admin.register(Gancfouthsession)
class GancfouthsessionAdmin(BaseSessionAdmin):
    list_display = (
        "registerid",
        "get_facility",
        "get_province",
        "sessiontype",
        "sessionround",
        "sessiondate",
        "attendance",
        "presentga",
        "bp",
        "anemia",
        "antedepressionscreening",
        "birthplanningcounseling",
    )
    list_filter = (
        SessionProvinceFilter,
        "sessiontype",
        "sessiondate",
        "attendance",
        "dhypertension",
        "anemia",
        "antedepressionscreening",
        "antedepressiondiagnosed",
        "birthplanningcounseling",
    )
    search_fields = (
        "registerid__name",
        "registerid__fathername",
        "sessiontype",
        "typeofdangersign",
    )
    ordering = ("-sessiondate",)

    fieldsets = (
        ("Session Information", {
            "fields": (
                "registerid",
                "sessiontype",
                "sessionround",
                "sessiondate",
                "attendance",
                "presentga",
            )
        }),
        ("Maternal Assessment", {
            "fields": (
                "bp",
                "dhypertension",
                "rhypertensiontoMD",
                "weight",
                "anemia",
                "ironfolate",
                "ironfolatepluswomen",
                "pcalcium",
                "acalcium",
                "muac",
                "dmam",
                "rmam",
                "dsam",
                "rsam",
            )
        }),
        ("Mental Health", {
            "fields": (
                "antedepressionscreening",
                "antedepressiondiagnosed",
                "rpsychosocialcounselor",
            )
        }),
        ("Laboratory and Screening", {
            "fields": (
                "urinexam",
                "rpositivepuriatomd",
                "coughmorethantwoweeks",
                "rcough",
                "ttvaccine",
            )
        }),
        ("Danger Signs and Counseling", {
            "fields": (
                "dangersign",
                "typeofdangersign",
                "birthplanningcounseling",
            )
        }),
        ("Other Information", {
            "fields": ("remarks",)
        }),
    )


# ============================================================
# Delivery
# ============================================================

@admin.register(Gancdelivery)
class GancdeliveryAdmin(BaseSessionAdmin):
    list_display = (
        "registerid",
        "get_facility",
        "get_province",
        "date_of_delivery",
        "gestational_age_at_delivery",
        "place_of_delivery",
        "type_of_delivery",
        "maternal_death",
        "number_of_newborn",
        "number_of_alive_newborn",
        "number_of_newborn_death",
        "number_of_fresh_still_birth",
    )
    list_filter = (
        SessionProvinceFilter,
        "date_of_delivery",
        "place_of_delivery",
        "type_of_delivery",
        "maternal_death",
        "early_breastfeeding",
        "newborn_vaccination_before_discharge",
        "counseled_on_postpartum_fp_before_discharge",
        "immediate_ppfp_before_discharge",
    )
    search_fields = (
        "registerid__name",
        "registerid__fathername",
        "types_of_complication",
        "how_complication_was_managed",
    )
    ordering = ("-date_of_delivery",)

    fieldsets = (
        ("Delivery Information", {
            "fields": (
                "registerid",
                "date_of_delivery",
                "gestational_age_at_delivery",
                "place_of_delivery",
                "type_of_delivery",
                "immediate_uterotonic_for_amtsl",
            )
        }),
        ("Complications", {
            "fields": (
                "types_of_complication",
                "how_complication_was_managed",
                "maternal_death",
            )
        }),
        ("Newborn Outcome", {
            "fields": (
                "number_of_newborn",
                "number_of_alive_newborn",
                "number_of_newborn_death",
                "number_of_fresh_still_birth",
                "early_breastfeeding",
                "newborn_vaccination_before_discharge",
            )
        }),
        ("Postpartum Family Planning", {
            "fields": (
                "counseled_on_postpartum_fp_before_discharge",
                "immediate_ppfp_before_discharge",
                "ppfp_method_taken_before_discharge",
            )
        }),
        ("Other Information", {
            "fields": ("remark",)
        }),
    )


# ============================================================
# PNC First Session
# ============================================================

@admin.register(GroupPncfirstSession)
class GroupPncfirstSessionAdmin(BaseSessionAdmin):
    list_display = (
        "registerid",
        "get_facility",
        "get_province",
        "session_type",
        "session_round",
        "session_date",
        "post_natal_day",
        "attendance",
        "diagnosed_with_hypertension",
        "anemia",
        "newborn_death",
        "maternal_death",
    )
    list_filter = (
        SessionProvinceFilter,
        "session_type",
        "session_date",
        "attendance",
        "diagnosed_with_hypertension",
        "anemia",
        "newborn_death",
        "maternal_death",
        "exclusive_breast_feeding",
        "chosen_ppfp_method",
    )
    search_fields = (
        "registerid__name",
        "registerid__fathername",
        "type_of_maternal_danger_sign",
        "type_of_newborn_danger_sign",
    )
    ordering = ("-session_date",)

    fieldsets = (
        ("Session Information", {
            "fields": (
                "registerid",
                "session_type",
                "session_round",
                "session_date",
                "post_natal_day",
                "attendance",
            )
        }),
        ("Maternal Assessment", {
            "fields": (
                "bp",
                "diagnosed_with_hypertension",
                "referred_hypertension_to_md",
                "muac",
                "diagnosed_with_mam",
                "refer_mam_to_nutrition_counselor",
                "diagnosed_with_sam",
                "refer_sam_to_higher_level",
                "anemia",
                "iron_folate_routine_dose",
                "iron_folate_plus_for_anemic_woman",
            )
        }),
        ("Danger Signs and Outcome", {
            "fields": (
                "type_of_maternal_danger_sign",
                "type_of_newborn_danger_sign",
                "newborn_death",
                "maternal_death",
            )
        }),
        ("Laboratory and Screening", {
            "fields": (
                "urine_exam",
                "protein_uria",
                "referred_positive_protein_uria_to_md",
                "cough_more_than_two_weeks",
                "referred_cough_to_dots_room",
            )
        }),
        ("Newborn and FP", {
            "fields": (
                "newborn_vaccination_completed",
                "exclusive_breast_feeding",
                "chosen_ppfp_method",
                "ppfp_method_taken",
            )
        }),
        ("Other Information", {
            "fields": ("remark",)
        }),
    )


# ============================================================
# PNC Second Session
# ============================================================

@admin.register(GroupPncsecondSession)
class GroupPncsecondSessionAdmin(BaseSessionAdmin):
    list_display = (
        "registerid",
        "get_facility",
        "get_province",
        "sessiontype",
        "sessionround",
        "sessiondate",
        "postnatalday",
        "attendance",
        "dhypertension",
        "anemia",
        "newborndeath",
        "maternaldeath",
        "birthspacingmethodchosen",
    )
    list_filter = (
        SessionProvinceFilter,
        "sessiontype",
        "sessiondate",
        "attendance",
        "dhypertension",
        "anemia",
        "newborndeath",
        "maternaldeath",
        "exclusivebreastfeeding",
        "birthspacingmethodchosen",
        "postnataldepressiondiagnosed",
    )
    search_fields = (
        "registerid__name",
        "registerid__fathername",
        "typeofmaternaldangersign",
        "typeofnewborndangersign",
    )
    ordering = ("-sessiondate",)

    fieldsets = (
        ("Session Information", {
            "fields": (
                "registerid",
                "sessiontype",
                "sessionround",
                "sessiondate",
                "postnatalday",
                "attendance",
            )
        }),
        ("Maternal Assessment", {
            "fields": (
                "bp",
                "dhypertension",
                "rhypertensiontomd",
                "muac",
                "dmam",
                "rmam",
                "dsam",
                "rsam",
                "anemia",
                "ironfolate",
                "ironfolatepluswomen",
            )
        }),
        ("Mental Health", {
            "fields": (
                "postnataldepressiondiagnosed",
                "rpsychosocialcounselor",
            )
        }),
        ("Danger Signs and Outcome", {
            "fields": (
                "typeofmaternaldangersign",
                "typeofnewborndangersign",
                "newborndeath",
                "maternaldeath",
            )
        }),
        ("Other Health Information", {
            "fields": (
                "newbornvaccinationcompleted",
                "coughmorethantwoweeks",
                "rcough",
                "exclusivebreastfeeding",
            )
        }),
        ("Birth Spacing", {
            "fields": (
                "birthspacingmethodchosen",
                "birthspacingmethod",
            )
        }),
        ("Other Information", {
            "fields": ("remark",)
        }),
    )
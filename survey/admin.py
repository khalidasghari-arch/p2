from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from . import models
from django.utils import timezone
from hiva.admin_utils import user_province

# def user_province(request):
#     """
#     Returns Province object for normal users.
#     Returns None for superuser (meaning: no restriction).
#     """
#     if request.user.is_superuser:
#         return None

#     prof = getattr(request.user, "profile", None)
#     return getattr(prof, "province", None)

class ProvincePhaseFilter(SimpleListFilter):
    title = "Province phase"
    parameter_name = "prov_phase"

    def lookups(self, request, model_admin):
        return ((1, "Phase 1"), (2, "Phase 2"), (3, "Phase 3"))

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(facility__districtfk__provincefk__phase=self.value())
        return queryset

class ProvinceFilter(SimpleListFilter):
    title = "Province"
    parameter_name = "province"

    def lookups(self, request, model_admin):
        qs = (
            models.PatientSafetyHeader.objects
            .select_related("facility__districtfk__provincefk")
            .values_list("facility__districtfk__provincefk__id",
                         "facility__districtfk__provincefk__name")
            .distinct()
            .order_by("facility__districtfk__provincefk__name")
        )
        return [(pid, pname) for pid, pname in qs if pid and pname]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(facility__districtfk__provincefk__id=self.value())
        return queryset

@admin.register(models.WorkArea)
class WorkAreaAdmin(admin.ModelAdmin):
    list_display = ("id", "work_area_name")
    search_fields = ("work_area_name",)
    ordering = ("work_area_name",)

class PatientSafetyDetailsInline(admin.StackedInline):
    model = models.PatientSafetyDetails
    extra = 0
    max_num = 1
    can_delete = False
    exclude = ("created_by", "updated_by", "created_at", "updated_at")

    fieldsets = (
        ("Work Area", {"fields": ("work_area",)}),
        ("Section A (A1–A14)", {"fields": (
            ("a1", "a2", "a3"),
            ("a4", "a5", "a6"),
            ("a7", "a8", "a9"),
            ("a10", "a11", "a12"),
            ("a13", "a14"),
        )}),
        ("Section B (B1–B3)", {"fields": (("b1", "b2", "b3"),)}),
        ("Section C (C1–C7)", {"fields": (
            ("c1", "c2", "c3"),
            ("c4", "c5", "c6"),
            ("c7",),
        )}),
        ("Section D (D1–D3)", {"fields": (("d1", "d2", "d3"),)}),
        ("Section E (E1)", {"fields": ("e1",)}),
        ("Section F (F1–F6)", {"fields": (("f1", "f2", "f3"), ("f4", "f5", "f6"))}),
        ("Section G (G1–G4)", {"fields": (("g1", "g2", "g3", "g4"),)}),
        ("Your Comments", {"fields": ("comment",)}),
    )

@admin.register(models.PatientSafetyHeader)
class PatientSafetyHeaderAdmin(admin.ModelAdmin):
    inlines = [PatientSafetyDetailsInline]

    list_display = (
        "id", "key_intervention_name", "facility", "get_province",
        "surveymonth", "surveyyear", "assessor", "created_at",
    )

    search_fields = (
        "key_intervention_name",
        "facility__name",
        "facility__hfcode",
        "assessor__name",
        "staff_profession__name",
        "facility__districtfk__provincefk__name",
        "facility__districtfk__name",
    )

    list_filter = (
        "status",
        ProvincePhaseFilter,
        ProvinceFilter,
        "surveyyear",
        "surveymonth",
        "facility__facilitytypefk",
        "assessor",
    )

    actions = ["mark_submitted", "approve_selected", "reject_selected"]

    readonly_fields = ("submitted_by", "submitted_at", "approved_by", "approved_at")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        prov = user_province(request)
        if prov is None:
            return qs
        return qs.filter(facility__districtfk__provincefk=prov)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # limit facility dropdown by province
        if db_field.name == "facility" and not request.user.is_superuser:
            prov = user_province(request)
            if prov:
                kwargs["queryset"] = models.PatientSafetyHeader._meta.get_field("facility").remote_field.model.objects.filter(
                    districtfk__provincefk=prov
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.action(description="Mark selected as Submitted")
    def mark_submitted(self, request, queryset):
        queryset = self.get_queryset(request).filter(pk__in=queryset.values_list("pk", flat=True))
        queryset.update(
            status="submitted",
            submitted_by=request.user,
            submitted_at=timezone.now(),
        )

    @admin.action(description="Approve selected")
    def approve_selected(self, request, queryset):
        if not request.user.is_superuser:
            # optional: allow only superuser to approve
            self.message_user(request, "Only superuser can approve.", level="ERROR")
            return
        queryset.update(
            status="approved",
            approved_by=request.user,
            approved_at=timezone.now(),
        )

    @admin.action(description="Reject selected")
    def reject_selected(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, "Only superuser can reject.", level="ERROR")
            return
        queryset.update(
            status="rejected",
            approved_by=request.user,
            approved_at=timezone.now(),
        )

    def has_change_permission(self, request, obj=None):
        # prevent editing after approval (except superuser)
        if request.user.is_superuser or obj is None:
            return True
        if obj.status == "approved":
            return False
        # also ensure province restriction
        return self.get_queryset(request).filter(pk=obj.pk).exists()

    ordering = ("-surveyyear", "-id")
    list_select_related = ("facility", "assessor", "staff_profession", "facility__districtfk__provincefk")

    fieldsets = (
        ("Survey Period", {"fields": ("surveymonth", "surveyyear", "key_intervention_name")}),
        ("Facility & Team", {"fields": ("facility", "assessor", "staff_profession")}),
    )

    @admin.display(description="Province")
    def get_province(self, obj):
        try:
            return obj.facility.districtfk.provincefk.name
        except Exception:
            return "-"

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in instances:
            if isinstance(obj, models.PatientSafetyDetails):
                if not obj.created_by_id:
                    obj.created_by = request.user
                obj.updated_by = request.user
            obj.save()
        formset.save_m2m()

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.is_superuser:
            actions.pop("approve_selected", None)
            actions.pop("reject_selected", None)
        return actions


@admin.register(models.PatientSafetyDetails)
class PatientSafetyDetailsAdmin(admin.ModelAdmin):
    list_display = ("id", "header", "work_area", "created_at", "updated_at")
    search_fields = ("header__facility__name", "header__assessor__name", "work_area__work_area_name")
    list_select_related = ("header", "work_area")
    ordering = ("-id",)

    def has_add_permission(self, request):
        return False

from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.utils import timezone
from django.utils.html import format_html

from . import models
from hiva.admin_utils import user_province

# ============================================================
# Filters
# ============================================================
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
            .values_list(
                "facility__districtfk__provincefk__id",
                "facility__districtfk__provincefk__name"
            )
            .distinct()
            .order_by("facility__districtfk__provincefk__name")
        )
        return [(pid, pname) for pid, pname in qs if pid and pname]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(facility__districtfk__provincefk__id=self.value())
        return queryset

# ============================================================
# WorkArea
# ============================================================
@admin.register(models.WorkArea)
class WorkAreaAdmin(admin.ModelAdmin):
    list_display = ("id", "work_area_name")
    search_fields = ("work_area_name",)
    ordering = ("work_area_name",)

# ============================================================
# Inline: PatientSafetyDetails (professional layout + guidance)
# ============================================================
class PatientSafetyDetailsInline(admin.StackedInline):
    model = models.PatientSafetyDetails
    extra = 0
    max_num = 1
    can_delete = False

    # Hide audit noise in inline
    exclude = ("created_by", "updated_by", "created_at", "updated_at")

    # Make all MCQ questions easy to select (radio buttons)
    radio_fields = {
        # A section
        "a1": admin.VERTICAL, "a2": admin.VERTICAL, "a3": admin.VERTICAL, "a4": admin.VERTICAL,
        "a5": admin.VERTICAL, "a6": admin.VERTICAL, "a7": admin.VERTICAL, "a8": admin.VERTICAL,
        "a9": admin.VERTICAL, "a10": admin.VERTICAL, "a11": admin.VERTICAL, "a12": admin.VERTICAL,
        "a13": admin.VERTICAL, "a14": admin.VERTICAL,

        # B section
        "b1": admin.VERTICAL, "b2": admin.VERTICAL, "b3": admin.VERTICAL,

        # C section
        "c1": admin.VERTICAL, "c2": admin.VERTICAL, "c3": admin.VERTICAL, "c4": admin.VERTICAL,
        "c5": admin.VERTICAL, "c6": admin.VERTICAL, "c7": admin.VERTICAL,

        # D section
        "d1": admin.VERTICAL, "d2": admin.VERTICAL, "d3": admin.VERTICAL,

        # E
        "e1": admin.VERTICAL,

        # F
        "f1": admin.VERTICAL, "f2": admin.VERTICAL, "f3": admin.VERTICAL,
        "f4": admin.VERTICAL, "f5": admin.VERTICAL, "f6": admin.VERTICAL,

        # G
        "g1": admin.VERTICAL, "g2": admin.VERTICAL, "g3": admin.VERTICAL, "g4": admin.VERTICAL,
    }

    # Add the new H section radio fields ONLY IF the fields exist in your model
    # (keeps admin error-free even if you haven't migrated yet)
    def get_radio_fields(self, request, obj=None):
        rf = dict(self.radio_fields)
        h_fields = [
            "h1_wrong_medication", "h2_wrong_dose", "h3_wrong_route", "h4_wrong_surgical_procedure",
            "h5_physical_abuse_ld", "h6_verbal_abuse_ld", "h7_stigma_discrimination",
            "h8_privacy_confidentiality", "h9_no_staff_at_birth",
            "h10_informed_consent", "h11_companionship_choice", "h12_treated_respectfully",
        ]
        model_field_names = {f.name for f in self.model._meta.get_fields()}
        for name in h_fields:
            if name in model_field_names:
                rf[name] = admin.VERTICAL
        return rf

    def get_formset(self, request, obj=None, **kwargs):
        # inject dynamic radio_fields safely
        self.radio_fields = self.get_radio_fields(request, obj)
        return super().get_formset(request, obj, **kwargs)

    # Read-only guidance labels (admin-only)
    readonly_fields = (
        "label_general",
        "label_likert_hint",
        "label_h_intro",
    )

    @admin.display(description="")
    def label_general(self, obj):
        return format_html(
            "<div style='padding:10px;border-left:4px solid #1f6feb;background:#f6f8fa;border-radius:6px;'>"
            "<b>Data entry tip:</b> Please answer honestly based on your experience. "
            "If you are unsure, select <b>9 (Does Not Apply / Don't Know)</b> where available."
            "</div>"
        )

    @admin.display(description="")
    def label_likert_hint(self, obj):
        return format_html(
            "<div style='padding:10px;border-left:4px solid #8250df;background:#f6f8fa;border-radius:6px;'>"
            "<b>Likert scale:</b> 1=Strongly Disagree … 5=Strongly Agree, 9=Does Not Apply/Don't Know."
            "</div>"
        )

    @admin.display(description="")
    def label_h_intro(self, obj):
        return format_html(
            "<div style='padding:10px;border-left:4px solid #238636;background:#f6f8fa;border-radius:6px;'>"
            "<b>Section H:</b> Frequency of events witnessed (medication/surgical errors) and Respectful Maternity Care "
            "(violations and positive practices)."
            "</div>"
        )

    # Fieldsets with collapsible groups (professional look)
    fieldsets = (
        ("Quick Guidance", {
            "fields": ("label_general", "label_likert_hint"),
        }),

        ("Work Area", {"fields": ("work_area",)}),

        ("SECTION A: Your Unit/Work Area How much do you agree or disagree with the following statements about your unit/work area?", {
            "classes": ("collapse",),
            "fields": (
                ("a1", "a2", "a3"),
                ("a4", "a5", "a6"),
                ("a7", "a8", "a9"),
                ("a10", "a11", "a12"),
                ("a13", "a14"),
            ),
        }),

        ("SECTION B: Your Supervisor, Manager, or Clinical Leader How much do you agree or disagree with the following statements about your immediate supervisor, manager, or clinical leader?", {
            "classes": ("collapse",),
            "fields": (("b1", "b2", "b3"),),
        }),

        ("SECTION C: Communication How often do the following things happen in your unit/work area?", {
            "classes": ("collapse",),
            "fields": (
                ("c1", "c2", "c3"),
                ("c4", "c5", "c6"),
                ("c7",),
            ),
        }),

        ("SECTION D: Reporting Patient Safety Events Think about your unit/work area:", {
            "classes": ("collapse",),
            "fields": (("d1", "d2", "d3"),),
        }),

        ("SECTION E: Patient Safety Rating How would you rate your unit/work area on patient safety?", {
            "classes": ("collapse",),
            "fields": ("e1",),
        }),

        ("SECTION F: Your Hospital How much do you agree or disagree with the following statements about your hospital?", {
            "classes": ("collapse",),
            "fields": (("f1", "f2", "f3"), ("f4", "f5", "f6")),
        }),

        # Section H only if fields exist (prevents admin crash)
        ("Section H – Medication/Surgical Errors & RMC", {
            "classes": ("collapse",),
            "fields": (),  # filled dynamically in get_fieldsets
        }),

        ("SECTION G: Background Questions", {
            "classes": ("collapse",),
            "fields": (("g1", "g2", "g3", "g4"),),
        }),

        ("Your Comments: Please feel free to provide any comments about how things are done or could be done in your hospital that might affect patient safety.", {"fields": ("comment",)}),
    )

    def get_fieldsets(self, request, obj=None):
        """
        Add Section H fieldsets only if those fields exist in DB/model.
        This keeps admin "zero error" even if migration isn't applied yet.
        """
        fs = list(super().get_fieldsets(request, obj))
        model_field_names = {f.name for f in self.model._meta.get_fields()}

        h_exists = any(
            f in model_field_names for f in (
                "h1_wrong_medication", "h10_informed_consent"
            )
        )
        if not h_exists:
            # remove the placeholder H section (last collapse group before G)
            fs = [x for x in fs if x[0] != "Section H – Medication/Surgical Errors & RMC"]
            return tuple(fs)

        # Replace placeholder with real Section H layout
        new_fs = []
        for title, opts in fs:
            if title != "Section H – Medication/Surgical Errors & RMC":
                new_fs.append((title, opts))
                continue

            new_fs.append((
                "Section H – Medication/Surgical Errors & RMC",
                {
                    "classes": ("collapse",),
                    "fields": (
                        "label_h_intro",
                        ("h1_wrong_medication", "h2_wrong_dose"),
                        ("h3_wrong_route", "h4_wrong_surgical_procedure"),
                        ("h5_physical_abuse_ld", "h6_verbal_abuse_ld"),
                        ("h7_stigma_discrimination", "h8_privacy_confidentiality"),
                        ("h9_no_staff_at_birth",),
                        ("h10_informed_consent", "h11_companionship_choice"),
                        ("h12_treated_respectfully",),
                    ),
                }
            ))
        return tuple(new_fs)

# ============================================================
# Header Admin (your same logic + clean UX)
# ============================================================
@admin.register(models.PatientSafetyHeader)
class PatientSafetyHeaderAdmin(admin.ModelAdmin):
    inlines = [PatientSafetyDetailsInline]

    list_display = (
        "id", "key_intervention_name", "facility", "get_province",
        "surveymonth", "surveyyear", "assessor", "status", "created_at",
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

    ordering = ("-surveyyear", "-id")
    list_select_related = ("facility", "assessor", "staff_profession", "facility__districtfk__provincefk")

    fieldsets = (
        ("Survey Period", {"fields": ("surveymonth", "surveyyear", "key_intervention_name")}),
        ("Facility & Team", {"fields": ("facility", "assessor", "staff_profession")}),
        ("Workflow", {
            "classes": ("collapse",),
            "fields": ("status", "submitted_by", "submitted_at", "approved_by", "approved_at", "approval_note"),
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        prov = user_province(request)
        if prov is None:
            return qs
        return qs.filter(facility__districtfk__provincefk=prov)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "facility" and not request.user.is_superuser:
            prov = user_province(request)
            facility_model = models.PatientSafetyHeader._meta.get_field("facility").remote_field.model
            if prov:
                kwargs["queryset"] = facility_model.objects.filter(districtfk__provincefk=prov)
            else:
                kwargs["queryset"] = facility_model.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.display(description="Province")
    def get_province(self, obj):
        try:
            return obj.facility.districtfk.provincefk.name
        except Exception:
            return "-"

    # ---- Actions ----
    @admin.action(description="Mark selected as Submitted")
    def mark_submitted(self, request, queryset):
        queryset = self.get_queryset(request).filter(pk__in=queryset.values_list("pk", flat=True))
        queryset.update(status="submitted", submitted_by=request.user, submitted_at=timezone.now())

    @admin.action(description="Approve selected")
    def approve_selected(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, "Only superuser can approve.", level="ERROR")
            return
        queryset.update(status="approved", approved_by=request.user, approved_at=timezone.now())

    @admin.action(description="Reject selected")
    def reject_selected(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, "Only superuser can reject.", level="ERROR")
            return
        queryset.update(status="rejected", approved_by=request.user, approved_at=timezone.now())

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser or obj is None:
            return True
        if obj.status == "approved":
            return False
        return self.get_queryset(request).filter(pk=obj.pk).exists()

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for o in instances:
            if isinstance(o, models.PatientSafetyDetails):
                if not o.created_by_id:
                    o.created_by = request.user
                o.updated_by = request.user
            o.save()
        formset.save_m2m()

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.is_superuser:
            actions.pop("approve_selected", None)
            actions.pop("reject_selected", None)
        return actions

# ============================================================
# Details Admin (view-only list)
# ============================================================
@admin.register(models.PatientSafetyDetails)
class PatientSafetyDetailsAdmin(admin.ModelAdmin):
    list_display = ("id", "header", "work_area", "created_at", "updated_at")
    search_fields = ("header__facility__name", "header__assessor__name", "work_area__work_area_name")
    list_select_related = ("header", "work_area")
    ordering = ("-id",)

    def has_add_permission(self, request):
        return False

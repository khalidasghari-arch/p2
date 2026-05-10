from django.contrib import admin, messages
from django import forms
from django.core.exceptions import FieldError
from django.db.models import Count
from django.http import JsonResponse
from django.urls import path
from django.utils.html import format_html

from .models import (
    ThematicArea,
    SkillLabTopic,
    SkillLab,
    SkillLabSession,
    SkillLabParticipantRecord,
    Skill_Lab_Mentee,
)

try:
    from hiva.admin_utils import ProvinceRestrictedAdminMixin, user_province
except Exception:
    class ProvinceRestrictedAdminMixin:
        def province_filter_kwargs(self, request):
            return {}

    def user_province(request):
        return None


# =========================================================
# Helper functions
# =========================================================
def safe_filter_by_user_province(queryset, province):
    """
    Tries common province relation paths.
    This keeps the admin stable even if related hiva models use different FK names.
    """
    if not province:
        return queryset

    possible_paths = [
        "province",
        "provincefk",
        "districtfk__provincefk",
        "facility__districtfk__provincefk",
        "facilityfk__districtfk__provincefk",
        "hfname__districtfk__provincefk",
        "hf_name__districtfk__provincefk",
    ]

    for path in possible_paths:
        try:
            return queryset.filter(**{path: province})
        except FieldError:
            continue

    return queryset


def safe_order_by(queryset, *fields):
    for field in fields:
        try:
            return queryset.order_by(field)
        except FieldError:
            continue
    return queryset


# =========================================================
# Shared media mixin for existing CSS + new cascade JS
# =========================================================
class SkillLabAdminMediaMixin:
    class Media:
        css = {
            "all": ("skilllab/admin/skilllab_admin.css",)
        }
        js = (
            "skilllab/admin/skilllab_cascade_topics.js",
        )


# =========================================================
# Filters
# =========================================================
class SkillLabProvinceFilter(admin.SimpleListFilter):
    title = "Province"
    parameter_name = "province"

    def lookups(self, request, model_admin):
        from hiva.models import Province
        return [(p.pk, p.name) for p in Province.objects.all().order_by("name")]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(facility__districtfk__provincefk_id=self.value())
        return queryset


class SkillLabSessionProvinceFilter(admin.SimpleListFilter):
    title = "Province"
    parameter_name = "province"

    def lookups(self, request, model_admin):
        from hiva.models import Province
        return [(p.pk, p.name) for p in Province.objects.all().order_by("name")]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(skill_lab__facility__districtfk__provincefk_id=self.value())
        return queryset


class ParticipantProvinceFilter(admin.SimpleListFilter):
    title = "Province"
    parameter_name = "province"

    def lookups(self, request, model_admin):
        from hiva.models import Province
        return [(p.pk, p.name) for p in Province.objects.all().order_by("name")]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(session__skill_lab__facility__districtfk__provincefk_id=self.value())
        return queryset


# =========================================================
# Forms
# =========================================================
class SkillLabParticipantRecordForm(forms.ModelForm):
    class Meta:
        model = SkillLabParticipantRecord
        fields = "__all__"
        widgets = {
            "remarks": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "ls" in self.fields:
            self.fields["ls"].label = "Learning Session (LS)"
        if "mc" in self.fields:
            self.fields["mc"].label = "MODEL COMPOTENT(MC)"

        # -----------------------------------------
        # Cascading topic queryset by thematic area
        # Works for direct form and inline form prefixes.
        # -----------------------------------------
        if "topic" in self.fields:
            thematic_id = None

            # Inline field name usually looks like:
            # participant_records-0-thematic_area
            if self.data and self.prefix:
                prefixed_key = f"{self.prefix}-thematic_area"
                thematic_id = self.data.get(prefixed_key)

            # Direct change form field name
            if not thematic_id and self.data:
                thematic_id = self.data.get("thematic_area")

            # Existing saved object
            if not thematic_id and self.instance.pk and getattr(self.instance, "thematic_area_id", None):
                thematic_id = self.instance.thematic_area_id

            if thematic_id:
                try:
                    self.fields["topic"].queryset = SkillLabTopic.objects.filter(
                        thematicfk_id=int(thematic_id)
                    ).order_by("track", "seq_no", "name")
                except (TypeError, ValueError):
                    self.fields["topic"].queryset = SkillLabTopic.objects.none()
            else:
                self.fields["topic"].queryset = SkillLabTopic.objects.none()


class SkillLabSessionAdminForm(forms.ModelForm):
    class Meta:
        model = SkillLabSession
        fields = "__all__"
        widgets = {
            "objectives": forms.Textarea(attrs={"rows": 2}),
            "session_notes": forms.Textarea(attrs={"rows": 3}),
            "challenges": forms.Textarea(attrs={"rows": 2}),
            "action_points": forms.Textarea(attrs={"rows": 2}),
        }


# =========================================================
# Inline
# =========================================================
class SkillLabParticipantRecordInline(admin.TabularInline):
    model = SkillLabParticipantRecord
    form = SkillLabParticipantRecordForm
    extra = 1
    show_change_link = True
    classes = ("tabular-inline-modern",)

    # Keep thematic as autocomplete. Topic must be normal dropdown for cascade.
    autocomplete_fields = ("thematic_area",)
    raw_id_fields = ("mentee_name",)

    fields = (
        "mentee_name",
        "thematic_area",
        "topic",
        "ls",
        "mc",
        "competency_status",
        "checklist_score",
        "feedback_given",
    )

    verbose_name = "Participant Record"
    verbose_name_plural = "Participant Records"

    class Media:
        js = (
            "skilllab/admin/skilllab_cascade_topics.js",
        )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        province = user_province(request)

        # Show all mentees in user's province, not only the skill lab facility.
        if db_field.name == "mentee_name" and province and not request.user.is_superuser:
            kwargs["queryset"] = Skill_Lab_Mentee.objects.filter(
                hfname__districtfk__provincefk=province
            ).select_related("hfname", "position").order_by("firstname", "lastname")

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

# =========================================================
# Thematic Area
# =========================================================
@admin.register(ThematicArea)
class ThematicAreaAdmin(SkillLabAdminMediaMixin, admin.ModelAdmin):
    list_display = ("name", "shortname", "hqip_area")
    search_fields = ("name", "shortname", "hqip_area__name")
    list_select_related = ("hqip_area",)
    raw_id_fields = ("hqip_area",)


# =========================================================
# Skill Lab Topic
# =========================================================
@admin.register(SkillLabTopic)
class SkillLabTopicAdmin(SkillLabAdminMediaMixin, admin.ModelAdmin):
    list_display = ("name", "shortname", "thematicfk", "nameeng")
    search_fields = ("name", "shortname", "thematicfk__name", "nameeng")
    list_filter = ("thematicfk",)
    autocomplete_fields = ("thematicfk",)


# =========================================================
# Skill Lab
# =========================================================
@admin.register(SkillLab)
class SkillLabAdmin(SkillLabAdminMediaMixin, ProvinceRestrictedAdminMixin, admin.ModelAdmin):
    list_display = (
        "name",
        "facility",
        "get_district",
        "get_province",
        "status_badge",
        "implementing_partner",
        "session_count",
    )
    search_fields = (
        "name",
        "facility__name",
        "facility__districtfk__name",
        "facility__districtfk__provincefk__name",
        "implementing_partner__name",
    )
    list_filter = (SkillLabProvinceFilter, "status", "implementing_partner")
    list_select_related = (
        "facility",
        "facility__districtfk",
        "facility__districtfk__provincefk",
        "implementing_partner",
    )
    raw_id_fields = ("facility", "implementing_partner")

    fieldsets = (
        ("MNH SKILL LAB INFORMATION", {
            "fields": ("name", "facility", "status", "implementing_partner"),
            "classes": ("wide", "skilllab-card"),
        }),
        ("Notes", {
            "fields": ("remarks",),
            "classes": ("collapse", "skilllab-card"),
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related(
            "facility",
            "facility__districtfk",
            "facility__districtfk__provincefk",
            "implementing_partner",
        ).annotate(_session_count=Count("sessions"))

        province = user_province(request)
        if province and not request.user.is_superuser:
            qs = qs.filter(facility__districtfk__provincefk=province)
        return qs

    def province_filter_kwargs(self, request):
        return {"facility__districtfk__provincefk": user_province(request)}

    @admin.display(description="District")
    def get_district(self, obj):
        return getattr(obj.facility.districtfk, "name", "-") if obj.facility else "-"

    @admin.display(description="Province")
    def get_province(self, obj):
        try:
            return obj.facility.districtfk.provincefk.name
        except Exception:
            return "-"

    @admin.display(description="Sessions")
    def session_count(self, obj):
        return getattr(obj, "_session_count", 0)

    @admin.display(description="Status")
    def status_badge(self, obj):
        css_map = {
            "ACTIVE": "sl-badge sl-badge-success",
            "INACTIVE": "sl-badge sl-badge-muted",
            "PLANNED": "sl-badge sl-badge-warning",
            "CLOSED": "sl-badge sl-badge-danger",
        }
        cls = css_map.get(obj.status, "sl-badge")
        return format_html('<span class="{}">{}</span>', cls, obj.get_status_display())


# =========================================================
# Skill Lab Session
# =========================================================
@admin.register(SkillLabSession)
class SkillLabSessionAdmin(SkillLabAdminMediaMixin, ProvinceRestrictedAdminMixin, admin.ModelAdmin):
    form = SkillLabSessionAdminForm
    inlines = [SkillLabParticipantRecordInline]

    list_display = (
        "skill_lab",
        "get_province",
        "session_date",
        "lab_round",
        "session_type_badge",
        "mentor_name",
        "ce_checklist_applied",
        "completed_session",
        "participant_total_display",
        "duration_display",
    )
    search_fields = (
        "skill_lab__name",
        "skill_lab__facility__name",
        "skill_lab__facility__districtfk__name",
        "skill_lab__facility__districtfk__provincefk__name",
    )
    list_filter = (
        SkillLabSessionProvinceFilter,
        "session_type",
        "lab_round",
        "ce_checklist_applied",
        "completed_session",
        "planned_session",
        "followup_needed",
        "session_date",
    )
    date_hierarchy = "session_date"
    save_on_top = True
    list_per_page = 50

    autocomplete_fields = ("skill_lab",)
    raw_id_fields = ("mentor_org",)

    readonly_fields = (
        "duration_preview",
        "participant_total_readonly",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        ("Skill Lab Header Information", {
            "fields": (
                "skill_lab",
                "session_date",
                ("lab_round", "session_type"),
            ),
            "classes": ("wide", "skilllab-card"),
        }),
        ("Time and Attendance", {
            "fields": (
                ("check_in", "check_out"),
                "duration_preview",
                ("planned_session", "completed_session"),
                ("total_participants", "participant_total_readonly"),
            ),
            "classes": ("wide", "skilllab-card"),
        }),
        ("Facilitation and Follow-up", {
            "fields": (
                ("mentor_name", "mentor_org"),
                "ce_checklist_applied",
                "followup_needed",
            ),
            "classes": ("wide", "skilllab-card"),
        }),
        ("Documentation", {
            "fields": ("objectives", "session_notes", "challenges", "action_points"),
            "classes": ("collapse", "skilllab-card"),
        }),
        ("Audit Trail", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse", "skilllab-card"),
        }),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "topics-by-thematic/",
                self.admin_site.admin_view(self.topics_by_thematic),
                name="skilllab_topics_by_thematic",
            ),
        ]
        return custom_urls + urls

    def topics_by_thematic(self, request):
        thematic_id = request.GET.get("thematic_id")
        topics = SkillLabTopic.objects.none()

        if thematic_id:
            topics = SkillLabTopic.objects.filter(
                thematicfk_id=thematic_id
            ).order_by("track", "seq_no", "name")

        data = [
            {
                "id": topic.pk,
                "text": str(topic),
            }
            for topic in topics
        ]
        return JsonResponse({"results": data})

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        province = user_province(request)

        # If mentor_name has been converted to FK to hiva.Assessor,
        # restrict it to clinical mentors in the user's province.
        # If mentor_name is still CharField, this method is not called for it.
        if db_field.name in ("mentor_name", "mentor") and province and not request.user.is_superuser:
            qs = db_field.remote_field.model.objects.all()
            qs = safe_filter_by_user_province(qs, province)
            kwargs["queryset"] = safe_order_by(qs, "name", "firstname", "first_name")

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related(
            "skill_lab",
            "skill_lab__facility",
            "skill_lab__facility__districtfk",
            "skill_lab__facility__districtfk__provincefk",
            "mentor_org",
        ).annotate(_participant_count=Count("participant_records"))

        province = user_province(request)
        if province and not request.user.is_superuser:
            qs = qs.filter(skill_lab__facility__districtfk__provincefk=province)
        return qs

    def province_filter_kwargs(self, request):
        return {"skill_lab__facility__districtfk__provincefk": user_province(request)}

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        obj = form.instance
        actual_count = obj.participant_records.count()
        if obj.total_participants != actual_count:
            obj.total_participants = actual_count
            obj.save(update_fields=["total_participants"])
            self.message_user(
                request,
                f"Total participants updated automatically to {actual_count}.",
                level=messages.INFO,
            )

    @admin.display(description="Facility")
    def get_facility(self, obj):
        return obj.skill_lab.facility.name if obj.skill_lab and obj.skill_lab.facility else "-"

    @admin.display(description="Province")
    def get_province(self, obj):
        try:
            return obj.skill_lab.facility.districtfk.provincefk.name
        except Exception:
            return "-"

    @admin.display(description="Type")
    def session_type_badge(self, obj):
        css_map = {
            "LS": "sl-badge sl-badge-primary",
            "MC": "sl-badge sl-badge-success",
            "PC": "sl-badge sl-badge-warning",
            "OTHER": "sl-badge sl-badge-muted",
        }
        cls = css_map.get(obj.session_type, "sl-badge")
        return format_html('<span class="{}">{}</span>', cls, obj.get_session_type_display())

    @admin.display(description="Participants")
    def participant_total_display(self, obj):
        return getattr(obj, "_participant_count", 0)

    @admin.display(description="Current Participant Count")
    def participant_total_readonly(self, obj):
        if not obj.pk:
            return 0
        return obj.participant_records.count()

    @admin.display(description="Duration")
    def duration_display(self, obj):
        if obj.duration_hours is None:
            return "-"
        css = "sl-duration-ok" if obj.duration_hours <= 8 else "sl-duration-warn"
        return format_html('<span class="{}">{} hrs</span>', css, obj.duration_hours)

    @admin.display(description="Duration Preview")
    def duration_preview(self, obj):
        if not obj.pk:
            return "Will appear after save"
        if obj.duration_hours is None:
            return "-"
        return f"{obj.duration_hours} hours"


# =========================================================
# Participant Record
# =========================================================
@admin.register(SkillLabParticipantRecord)
class SkillLabParticipantRecordAdmin(SkillLabAdminMediaMixin, ProvinceRestrictedAdminMixin, admin.ModelAdmin):
    form = SkillLabParticipantRecordForm

    list_display = (
        "mentee_name",
        "get_skill_lab",
        "get_session_date",
        "get_province",
        "thematic_area",
        "topic",
        "method_display",
        "competency_badge",
        "score_summary",
    )
    search_fields = (
        "mentee_name__firstname",
        "mentee_name__lastname",
        "mentee_name__fathername",
        "mentee_name__tazkiranumber",
        "session__skill_lab__name",
        "session__skill_lab__facility__name",
        "topic__name",
        "topic__nameeng",
        "thematic_area__name",
    )
    list_filter = (
        ParticipantProvinceFilter,
        "competency_status",
        "ls",
        "mc",
        "thematic_area",
    )
    list_select_related = (
        "session",
        "session__skill_lab",
        "session__skill_lab__facility",
        "session__skill_lab__facility__districtfk",
        "session__skill_lab__facility__districtfk__provincefk",
        "thematic_area",
        "topic",
        "mentee_name",
    )
    list_per_page = 50

    # Topic is normal dropdown for cascade.
    autocomplete_fields = ("session", "thematic_area")
    raw_id_fields = ("mentee_name",)

    fieldsets = (
        ("Participant Information", {
            "fields": (
                "session",
                "mentee_name",
            ),
            "classes": ("wide", "skilllab-card"),
        }),
        ("Topic and Method", {
            "fields": (
                ("thematic_area", "topic"),
                ("ls", "mc"),
                "competency_status",
            ),
            "classes": ("wide", "skilllab-card"),
        }),
        ("Assessment", {
            "fields": (
                ("pre_test_score", "post_test_score", "checklist_score"),
                ("demonstration_done", "return_demonstration_done"),
                "feedback_given",
                "next_followup_date",
            ),
            "classes": ("wide", "skilllab-card"),
        }),
        ("Remarks", {
            "fields": ("remarks",),
            "classes": ("collapse", "skilllab-card"),
        }),
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        province = user_province(request)

        # Show all mentees in user's province, not limited to one facility.
        if db_field.name == "mentee_name" and province and not request.user.is_superuser:
            kwargs["queryset"] = Skill_Lab_Mentee.objects.filter(
                hfname__districtfk__provincefk=province
            ).select_related("hfname", "position").order_by("firstname", "lastname")

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related(
            "session",
            "session__skill_lab",
            "session__skill_lab__facility",
            "session__skill_lab__facility__districtfk",
            "session__skill_lab__facility__districtfk__provincefk",
            "thematic_area",
            "topic",
            "mentee_name",
        )
        province = user_province(request)
        if province and not request.user.is_superuser:
            qs = qs.filter(session__skill_lab__facility__districtfk__provincefk=province)
        return qs

    def province_filter_kwargs(self, request):
        return {"session__skill_lab__facility__districtfk__provincefk": user_province(request)}

    @admin.display(description="Skill Lab")
    def get_skill_lab(self, obj):
        return obj.session.skill_lab.name if obj.session_id else "-"

    @admin.display(description="Date")
    def get_session_date(self, obj):
        return obj.session.session_date if obj.session_id else "-"

    @admin.display(description="Province")
    def get_province(self, obj):
        try:
            return obj.session.skill_lab.facility.districtfk.provincefk.name
        except Exception:
            return "-"

    @admin.display(description="Method")
    def method_display(self, obj):
        vals = []
        if obj.ls:
            vals.append("LS")
        if obj.mc:
            vals.append("MC")
        return ", ".join(vals) if vals else "-"

    @admin.display(description="Competency")
    def competency_badge(self, obj):
        css_map = {
            "NOT_STARTED": "sl-badge sl-badge-muted",
            "IN_PROGRESS": "sl-badge sl-badge-warning",
            "COMPETENT": "sl-badge sl-badge-success",
            "NEEDS_REPEAT": "sl-badge sl-badge-danger",
        }
        cls = css_map.get(obj.competency_status, "sl-badge")
        return format_html('<span class="{}">{}</span>', cls, obj.get_competency_status_display())

    @admin.display(description="Scores")
    def score_summary(self, obj):
        parts = []
        if obj.pre_test_score is not None:
            parts.append(f"Pre: {obj.pre_test_score}")
        if obj.post_test_score is not None:
            parts.append(f"Post: {obj.post_test_score}")
        if obj.checklist_score is not None:
            parts.append(f"CL: {obj.checklist_score}")
        return " | ".join(parts) if parts else "-"


# =========================================================
# Skill Lab Mentee
# =========================================================
@admin.register(Skill_Lab_Mentee)
class SkillLabMenteeAdmin(SkillLabAdminMediaMixin, ProvinceRestrictedAdminMixin, admin.ModelAdmin):
    list_display = (
        "firstname",
        "lastname",
        "fathername",
        "position",
        "hfname",
        "get_province",
        "status",
        "tazkiranumber",
    )
    search_fields = (
        "firstname",
        "lastname",
        "fathername",
        "tazkiranumber",
        "hfname__name",
        "hfname__districtfk__name",
        "hfname__districtfk__provincefk__name",
        "position__name",
    )
    list_filter = ("status", "position")
    raw_id_fields = ("hfname", "position")

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related(
            "hfname",
            "hfname__districtfk",
            "hfname__districtfk__provincefk",
            "position",
        )
        province = user_province(request)
        if province and not request.user.is_superuser:
            qs = qs.filter(hfname__districtfk__provincefk=province)
        return qs

    def province_filter_kwargs(self, request):
        return {"hfname__districtfk__provincefk": user_province(request)}

    @admin.display(description="Province")
    def get_province(self, obj):
        try:
            return obj.hfname.districtfk.provincefk.name
        except Exception:
            return "-"
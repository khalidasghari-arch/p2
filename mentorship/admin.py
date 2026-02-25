import re
from django.contrib import admin
from django import forms
from django.core.exceptions import ValidationError
from .models import (
    ThematicMentorship, MentorshipTopics, MenteeTopicStatus,
    Mentorshipvisit, Mentorshipdetails, Staff
)
from hiva.admin_utils import ProvinceRestrictedAdminMixin, user_province
from django.utils.html import format_html
from mentorship.recommender import recommend_next_for_staff_in_facility
from django.db.models import Count, Q
from django.utils.safestring import mark_safe
from django.template.response import TemplateResponse
from django.urls import path, reverse

# =====================================================
# Helpers
# =====================================================

def _prov_id(request):
    """
    Returns province id (int) safely.
    Works whether user_province returns Province object or id.
    """
    prov = user_province(request)
    if prov is None:
        return None
    return getattr(prov, "id", prov)

# =====================================================
# BASIC ADMINS
# =====================================================

@admin.register(ThematicMentorship)
class ThematicMentorshipAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "shortname", "hqip_area")
    search_fields = ("name", "shortname")

@admin.register(MentorshipTopics)
class MentorshipTopicsAdmin(admin.ModelAdmin):
    list_display = ("id", "thematicfk", "shortname", "name", "nameeng", "namedari", "namepashto")
    list_filter = ("thematicfk",)
    search_fields = ("name", "shortname", "namedari", "namepashto", "nameeng")

# =====================================================
# STAFF ADMIN (Province restriction + popup facility prefill)
# =====================================================

@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ("id", "hfname", "tazkiranumber", "firstname", "lastname", "fathername", "position", "gender", "status")
    list_filter = ("hfname", "status", "position")
    search_fields = ("firstname", "lastname", "tazkiranumber")

    def _facility_id_from_popup_context(self, request):
        """
        Priority:
          1) ?facility=<id> if present
          2) if popup opened from Mentorshipvisit change page, parse HTTP_REFERER
        """
        facility_id = request.GET.get("facility")
        if facility_id:
            return facility_id

        if request.GET.get("_popup") != "1":
            return None

        ref = request.META.get("HTTP_REFERER", "")
        m = re.search(r"/admin/mentorship/mentorshipvisit/(\d+)/change/?", ref)
        if not m:
            return None

        try:
            visit = Mentorshipvisit.objects.only("facilityfk_id").get(pk=m.group(1))
            return str(visit.facilityfk_id)
        except Mentorshipvisit.DoesNotExist:
            return None

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs

        prov_id = _prov_id(request)
        if prov_id is None:
            return qs.none()

        return qs.filter(hfname__districtfk__provincefk_id=prov_id)

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        facility_id = self._facility_id_from_popup_context(request)
        if facility_id:
            initial["hfname"] = facility_id
        return initial

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "hfname" and not request.user.is_superuser:
            Facility = db_field.remote_field.model

            facility_id = self._facility_id_from_popup_context(request)

            if facility_id:
                kwargs["queryset"] = Facility.objects.filter(pk=facility_id)
                field = super().formfield_for_foreignkey(db_field, request, **kwargs)
                field.initial = facility_id
                return field

            prov_id = _prov_id(request)
            kwargs["queryset"] = Facility.objects.filter(
                districtfk__provincefk_id=prov_id
            ).order_by("name") if prov_id else Facility.objects.none()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

# =====================================================
# INLINE FORM VALIDATION:
# - Only ONE of LS/PC/MC
# (REMOVED: topic-thematic matching rule)
# =====================================================

class MentorshipdetailsInlineForm(forms.ModelForm):
    class Meta:
        model = Mentorshipdetails
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()

        selected = sum([
            bool(cleaned.get("ls")),
            bool(cleaned.get("pc")),
            bool(cleaned.get("mc")),
        ])
        if selected > 1:
            raise ValidationError("Only ONE of (LS, PC, MC) can be selected.")

        return cleaned

# =====================================================
# DETAILS INLINE:
# - Mentee filtered by visit facility
# - Mentor filtered by user province
# - Topic dropdown shows ALL topics (NO FILTERING)
# =====================================================

class MentorshipdetailsInline(admin.TabularInline):
    model = Mentorshipdetails
    form = MentorshipdetailsInlineForm
    extra = 0

    def get_extra(self, request, obj=None, **kwargs):
        return 1 if obj else 0

    def has_add_permission(self, request, obj=None):
        if obj is None:
            return False
        return super().has_add_permission(request, obj=obj)

    def get_formset(self, request, obj=None, **kwargs):
        request._mentorship_parent_obj = obj
        return super().get_formset(request, obj, **kwargs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        parent_obj = getattr(request, "_mentorship_parent_obj", None)

        if db_field.name == "menteename":
            if parent_obj:
                kwargs["queryset"] = Staff.objects.filter(
                    hfname=parent_obj.facilityfk
                ).order_by("firstname", "lastname")
            else:
                kwargs["queryset"] = Staff.objects.none()

        if db_field.name == "mentor" and not request.user.is_superuser:
            prov_id = _prov_id(request)
            Assessor = db_field.remote_field.model
            kwargs["queryset"] = Assessor.objects.filter(
                province_id=prov_id
            ).order_by("id") if prov_id else Assessor.objects.none()

        # ✅ IMPORTANT: Always show ALL topics, no filtering, no JS, no endpoint
        if db_field.name == "topicname":
            kwargs["queryset"] = MentorshipTopics.objects.all().order_by(
                "thematicfk_id", "shortname", "name"
            )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

# =====================================================
# MENTORSHIP VISIT ADMIN:
# - Province restriction (Mixin)
# - Facility dropdown restricted by province
# - NO custom URLs
# - NO JS Media
# =====================================================
class MentorshipDashboardMixin:
    """
    Adds: /admin/mentorship/mentorshipvisit/facility-dashboard/<facility_id>/
    """

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "facility-dashboard/<int:facility_id>/",
                self.admin_site.admin_view(self.facility_dashboard_view),
                name="facility_mentorship_dashboard",
            ),
        ]
        return custom_urls + urls

    def facility_dashboard_view(self, request, facility_id):
        # Active mentees in this facility
        mentees = Staff.objects.filter(hfname_id=facility_id, status=True)
        total_mentees = mentees.count()

        # All topics
        total_topics = MentorshipTopics.objects.count()

        # All statuses for mentees in this facility
        statuses = MenteeTopicStatus.objects.filter(mentee__hfname_id=facility_id)

        competent_count = statuses.filter(status="COMPETENT").count()

        # Overall competency rate (competent topics / total possible)
        competency_rate = 0
        total_possible = total_mentees * total_topics
        if total_possible > 0:
            competency_rate = round((competent_count / total_possible) * 100)

        # Thematic breakdown
        thematic_stats = []
        thematics = ThematicMentorship.objects.all().order_by("name")

        for th in thematics:
            topic_count = MentorshipTopics.objects.filter(thematicfk=th).count()

            competent = MenteeTopicStatus.objects.filter(
                mentee__hfname_id=facility_id,
                topic__thematicfk=th,
                status="COMPETENT",
            ).count()

            total_possible_th = topic_count * total_mentees
            percent = 0
            if total_possible_th > 0:
                percent = round((competent / total_possible_th) * 100)

            thematic_stats.append({
                "name": th.name,
                "percent": percent,
            })

        # Escalation: LS >= 4 and not competent
        escalations = MenteeTopicStatus.objects.filter(
            mentee__hfname_id=facility_id,
            consecutive_ls__gte=4
        ).exclude(status="COMPETENT").select_related("mentee", "topic")

        context = dict(
            self.admin_site.each_context(request),
            title="Facility Mentorship Dashboard",
            total_mentees=total_mentees,
            competency_rate=competency_rate,
            thematic_stats=thematic_stats,
            escalations=escalations,
            facility_id=facility_id,
        )
        return TemplateResponse(request, "admin/mentorship/facility_dashboard.html", context)
    
@admin.register(Mentorshipvisit)
class MentorshipvisitAdmin(ProvinceRestrictedAdminMixin, 
MentorshipDashboardMixin, admin.ModelAdmin):

    list_display = (
        "facilityfk",
        "visitdate",
        "visitround",
        "mentorshipstarttime",
        "mentorshipendtime",
        "get_mentors",
        "ls_count",
        "pc_count",
        "mc_count",
        "mentees_count",
        "facility_dashboard_btn",
        "ai_recommendation",
        "id",
    )

    #list_filter = ("visitdate", "facilityfk")
    search_fields = ("facilityfk__name", "facilityfk__hfcode")
    readonly_fields = ("ai_recommendation",)
    list_per_page = 10
    inlines = (MentorshipdetailsInline,)

    @admin.display(description="Dashboard")
    def facility_dashboard_btn(self, obj):
        url = reverse("admin:facility_mentorship_dashboard", args=[obj.facilityfk_id])
        return format_html('<a class="button" href="{}">Dashboard</a>', url)

    # -------------------------------------------------
    # AI RECOMMENDATION (FIXED)
    # -------------------------------------------------
    @admin.display(description="Recommendation")
    def ai_recommendation(self, obj):

        # Get unique mentees in this visit
        mentee_ids = (
            obj.items
            .values_list("menteename_id", flat=True)
            .distinct()
        )

        if not mentee_ids:
            return "—"

        rows = []

        for mentee_id in mentee_ids:

            rec = recommend_next_for_staff_in_facility(
                staff_id=mentee_id,
                facility_id=obj.facilityfk_id
            )

            topic = rec["topic"]
            track = rec["track"]
            session = rec["session_type"]
            support = rec["support_flag"]

            # --- progress calculation ---
            total_topics = MentorshipTopics.objects.filter(
                thematicfk__name=track
            ).count()

            competent_count = MenteeTopicStatus.objects.filter(
                mentee_id=mentee_id,
                status="COMPETENT"
            ).count()

            progress = 0
            if total_topics > 0:
                progress = round((competent_count / total_topics) * 100)

            # --- session badge ---
            session_badge = ""
            if session == "LS":
                session_badge = '<span style="background:#1f77b4;color:white;padding:2px 6px;border-radius:4px;">LS</span>'
            elif session == "PC":
                session_badge = '<span style="background:#ff7f0e;color:white;padding:2px 6px;border-radius:4px;">PC</span>'
            elif session == "MC":
                session_badge = '<span style="background:#2ca02c;color:white;padding:2px 6px;border-radius:4px;">MC</span>'

            support_badge = ""
            if support:
                support_badge = '<span style="background:#d62728;color:white;padding:2px 6px;border-radius:4px;">YES</span>'
            else:
                support_badge = '<span style="background:#2ca02c;color:white;padding:2px 6px;border-radius:4px;">NO</span>'

            progress_color = "#d62728"
            if progress >= 70:
                progress_color = "#2ca02c"
            elif progress >= 40:
                progress_color = "#ff7f0e"

            progress_badge = f'<span style="background:{progress_color};color:white;padding:2px 6px;border-radius:4px;">{progress}%</span>'

            mentee_name = str(
                obj.items.filter(menteename_id=mentee_id).first().menteename
            )

            rows.append(f"""
                <tr>
                    <td><strong>{mentee_name}</strong></td>
                    <td>{track or '-'}</td>
                    <td>{topic.name if topic else '-'}</td>
                    <td>{session_badge}</td>
                    <td>{support_badge}</td>
                    <td>{progress_badge}</td>
                </tr>
            """)

        table = f"""
            <table style="border-collapse:collapse;width:100%;">
                <thead>
                    <tr style="background:#f5f5f5;">
                        <th style="padding:4px;border:1px solid #ddd;">Mentee</th>
                        <th style="padding:4px;border:1px solid #ddd;">Track</th>
                        <th style="padding:4px;border:1px solid #ddd;">Next Topic</th>
                        <th style="padding:4px;border:1px solid #ddd;">Session</th>
                        <th style="padding:4px;border:1px solid #ddd;">Support</th>
                        <th style="padding:4px;border:1px solid #ddd;">Progress</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        """

        return mark_safe(table)

    ai_recommendation.short_description = "AI Recommendation"

    # -------------------------------------------------
    # CLINICAL MENTOR DISPLAY
    # -------------------------------------------------
    @admin.display(description="Clinical Mentor")
    def get_mentors(self, obj):
        mentors = (
            obj.items
            .select_related("mentor")
            .values_list("mentor__name", flat=True)
            .distinct()
        )
        return ", ".join([m for m in mentors if m]) if mentors else "-"

    # -------------------------------------------------
    # LS / PC / MC COUNTS
    # -------------------------------------------------
    @admin.display(description="Total-LS")
    def ls_count(self, obj):
        return obj.items.filter(ls=True).count()

    @admin.display(description="Total-PC")
    def pc_count(self, obj):
        return obj.items.filter(pc=True).count()

    @admin.display(description="Total-MC")
    def mc_count(self, obj):
        return obj.items.filter(mc=True).count()

    # -------------------------------------------------
    # DISTINCT COUNTS
    # -------------------------------------------------
    @admin.display(description="Total-Mentee")
    def mentees_count(self, obj):
        return (
            obj.items
            .values("menteename")
            .exclude(menteename__isnull=True)
            .distinct()
            .count()
        )

    @admin.display(description="Total-Thematic Areas")
    def thematics_count(self, obj):
        return (
            obj.items
            .values("thematicname")
            .exclude(thematicname__isnull=True)
            .distinct()
            .count()
        )

    @admin.display(description="Total-Topics")
    def topics_count(self, obj):
        return (
            obj.items
            .values("topicname")
            .exclude(topicname__isnull=True)
            .distinct()
            .count()
        )

    # -------------------------------------------------
    # PERFORMANCE OPTIMIZATION (SINGLE VERSION)
    # -------------------------------------------------
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related(
            "items",
            "items__mentor",
            "items__menteename",
            "items__thematicname",
            "items__topicname",
        )

    # -------------------------------------------------
    # FIELDSETS
    # -------------------------------------------------
    fieldsets = (
        ("Mentorship Visit", {
            "fields": (
                "facilityfk",
                "visitdate",
                "visitround",
                "mentorshipstarttime",
                "mentorshipendtime",
                "ai_recommendation",
            )
        }),
    )

    # -------------------------------------------------
    # PROVINCE RESTRICTION
    # -------------------------------------------------
    def province_filter_kwargs(self, request):
        prov_id = _prov_id(request)
        return {"facilityfk__districtfk__provincefk_id": prov_id} if prov_id else {"pk__in": []}

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "facilityfk" and not request.user.is_superuser:
            Facility = db_field.remote_field.model
            prov_id = _prov_id(request)
            kwargs["queryset"] = Facility.objects.filter(
                districtfk__provincefk_id=prov_id
            ).order_by("name") if prov_id else Facility.objects.none()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

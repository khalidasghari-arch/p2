import re
from django.contrib import admin
from django import forms
from django.core.exceptions import ValidationError
from .models import (
    ThematicMentorship, MentorshipTopics,
    Mentorshipvisit, Mentorshipdetails, Staff
)
from hiva.admin_utils import ProvinceRestrictedAdminMixin, user_province

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
    list_display = ("id", "name", "shortname")
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

@admin.register(Mentorshipvisit)
class MentorshipvisitAdmin(ProvinceRestrictedAdminMixin, admin.ModelAdmin):
    list_display = ("facilityfk", "visitdate", "visitround", "mentorshipstarttime", 
    "mentorshipendtime", "get_mentors",  "ls_count",
    "pc_count", "mc_count",
    "mentees_count",
    "thematics_count",
    "topics_count","id", )
    list_filter = ("visitdate", "facilityfk")
    search_fields = ("facilityfk__name", "facilityfk__hfcode")
    list_per_page = 20
    inlines = (MentorshipdetailsInline,)

    def get_list_filter(self, request):
        if request.user.is_superuser:
            return self.list_filter
        return ()  # No filters for Clinical Mentors

    @admin.display(description="Clinical Mentor")
    def get_mentors(self, obj):
        mentors = (
            obj.items
            .select_related("mentor")
            .values_list("mentor__name", flat=True)  # change if Assessor uses another field
            .distinct()
        )
        return ", ".join([m for m in mentors if m]) if mentors else "-"
    
     # -----------------------------
    # LS / PC / MC counts
    # -----------------------------
    @admin.display(description="Total-LS")
    def ls_count(self, obj):
        return obj.items.filter(ls=True).count()

    @admin.display(description="Total-PC")
    def pc_count(self, obj):
        return obj.items.filter(pc=True).count()

    @admin.display(description="Total-MC")
    def mc_count(self, obj):
        return obj.items.filter(mc=True).count()

    # -----------------------------
    # Performance optimization
    # -----------------------------
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related("items", "items__mentor")
    
    # -----------------------------
    # DISTINCT COUNTS (important)
    # -----------------------------
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

    # -----------------------------
    # Performance optimization
    # -----------------------------
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related(
            "items",
            "items__mentor",
            "items__menteename",
            "items__thematicname",
            "items__topicname",
        )

    fieldsets = (
        ("Mentorship Visit", {
            "fields": (
                "facilityfk",
                "visitdate",
                "visitround",
                "mentorshipstarttime",
                "mentorshipendtime"
            )
        }),
    )

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

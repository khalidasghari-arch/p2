import re
from django.contrib import admin
from django import forms
from django.core.exceptions import ValidationError
from django.urls import path
from django.http import JsonResponse

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
    list_display = ("id", "hfname", "tazkiranumber", "firstname", "lastname", "position", "gender", "status")
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
        # Example: /admin/mentorship/mentorshipvisit/6/change/
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
            Facility = db_field.remote_field.model  # hiva.Facility

            facility_id = self._facility_id_from_popup_context(request)

            # Popup from mentorship visit: only that facility
            if facility_id:
                kwargs["queryset"] = Facility.objects.filter(pk=facility_id)
                field = super().formfield_for_foreignkey(db_field, request, **kwargs)
                field.initial = facility_id
                return field

            # Normal add/edit: restrict to user province
            prov_id = _prov_id(request)
            kwargs["queryset"] = Facility.objects.filter(
                districtfk__provincefk_id=prov_id
            ).order_by("name") if prov_id else Facility.objects.none()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# =====================================================
# INLINE FORM VALIDATION:
# - Only ONE of LS/PC/MC
# NOTE: Topic/thematic matching REMOVED (user requested no filtering)
# =====================================================

class MentorshipdetailsInlineForm(forms.ModelForm):
    class Meta:
        model = Mentorshipdetails
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()

        # Only one of LS/PC/MC
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
# - Topicname shows ALL topics (NO filtering)
# =====================================================

class MentorshipdetailsInline(admin.TabularInline):
    model = Mentorshipdetails
    form = MentorshipdetailsInlineForm
    extra = 0

    def get_extra(self, request, obj=None, **kwargs):
        # HQIP-style: show inline only after header saved
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

        # Mentee: only staff from parent facility
        if db_field.name == "menteename":
            if parent_obj:
                kwargs["queryset"] = Staff.objects.filter(
                    hfname=parent_obj.facilityfk
                ).order_by("firstname", "lastname")
            else:
                kwargs["queryset"] = Staff.objects.none()

        # Mentor (Assessor): restrict by province (SAFE: uses province_id)
        if db_field.name == "mentor" and not request.user.is_superuser:
            prov_id = _prov_id(request)
            Assessor = db_field.remote_field.model  # hiva.Assessor

            kwargs["queryset"] = Assessor.objects.filter(
                province_id=prov_id
            ).order_by("id") if prov_id else Assessor.objects.none()

        # ✅ Topicname: show ALL topics always (no filtering, no ajax)
        if db_field.name == "topicname":
            kwargs["queryset"] = MentorshipTopics.objects.all().order_by("thematicfk_id", "name")

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

# =====================================================
# MENTORSHIP VISIT ADMIN:
# - Province restriction (Mixin)
# - Facility dropdown restricted by province
# =====================================================

@admin.register(Mentorshipvisit)
class MentorshipvisitAdmin(ProvinceRestrictedAdminMixin, admin.ModelAdmin):
    list_display = ("id", "facilityfk", "visitdate", "visitround", "mentorshipstarttime", "mentorshipendtime")
    list_filter = ("visitdate", "facilityfk")
    search_fields = ("facilityfk__name", "facilityfk__hfcode")
    inlines = (MentorshipdetailsInline,)

    fieldsets = (
        ("Mentorship Visit", {
            "fields": (
                "facilityfk",
                ("visitdate", "visitround"),
                ("mentorshipstarttime", "mentorshipendtime"),
            )
        }),
    )

    # Province restriction for list/view/edit/delete (Mixin uses this)
    def province_filter_kwargs(self, request):
        prov_id = _prov_id(request)
        return {"facilityfk__districtfk__provincefk_id": prov_id} if prov_id else {"pk__in": []}

    # Restrict facility dropdown itself
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "facilityfk" and not request.user.is_superuser:
            Facility = db_field.remote_field.model  # hiva.Facility
            prov_id = _prov_id(request)
            kwargs["queryset"] = Facility.objects.filter(
                districtfk__provincefk_id=prov_id
            ).order_by("name") if prov_id else Facility.objects.none()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    class Media:
        # ✅ DO NOT load any custom JS (prevents disappearing dropdown problems)
        js = ()

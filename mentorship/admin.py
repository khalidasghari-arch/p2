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
# BASIC ADMINS (unchanged)
# =====================================================

@admin.register(ThematicMentorship)
class ThematicMentorshipAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "shortname")
    search_fields = ("name", "shortname")

@admin.register(MentorshipTopics)
class MentorshipTopicsAdmin(admin.ModelAdmin):
    list_display = ("id", "thematicfk", "name", "nameeng", "namedari", "namepashto")
    list_filter = ("thematicfk",)
    search_fields = ("name", "shortname", "namedari", "namepashto", "nameeng")

# =====================================================
# STAFF ADMIN (UNCHANGED – already working)
# =====================================================

@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ("id", "hfname", "tazkiranumber", "firstname", "lastname", "position", "gender", "status")
    list_filter = ("hfname", "status", "position")
    search_fields = ("firstname", "lastname", "tazkiranumber")

    def _facility_id_from_popup_context(self, request):
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
        prov = user_province(request)
        return qs.filter(hfname__districtfk__provincefk=prov) if prov else qs.none()

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

            prov = user_province(request)
            kwargs["queryset"] = Facility.objects.filter(
                districtfk__provincefk=prov
            ) if prov else Facility.objects.none()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# =====================================================
# INLINE FORM – enforce ONLY ONE of LS / PC / MC
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
            raise ValidationError("Only ONE of LS, PC, or MC can be selected.")
        return cleaned


# =====================================================
# INLINE – mentee by facility, topic by thematic, assessor by province
# =====================================================

class MentorshipdetailsInline(admin.TabularInline):
    model = Mentorshipdetails
    form = MentorshipdetailsInlineForm
    extra = 0

    def get_extra(self, request, obj=None, **kwargs):
        return 1 if obj else 0

    def has_add_permission(self, request, obj=None):
        return False if obj is None else super().has_add_permission(request, obj)

    def get_formset(self, request, obj=None, **kwargs):
        request._mentorship_parent_obj = obj
        return super().get_formset(request, obj, **kwargs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        parent_obj = getattr(request, "_mentorship_parent_obj", None)

        # 1️⃣ MENTEE → only staff from visit facility
        if db_field.name == "menteename":
            kwargs["queryset"] = (
                Staff.objects.filter(hfname=parent_obj.facilityfk)
                if parent_obj else Staff.objects.none()
            )

        # 2️⃣ TOPIC → only topics under selected thematic
        if db_field.name == "topicname":
            kwargs["queryset"] = MentorshipTopics.objects.none()

        # 3️⃣ MENTOR (ASSESSOR) → only assessor from user province
        if db_field.name == "mentor" and not request.user.is_superuser:
            Assessor = db_field.remote_field.model
            prov = user_province(request)
            kwargs["queryset"] = Assessor.objects.filter(
                province=prov
            ) if prov else Assessor.objects.none()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# =====================================================
# MENTORSHIP VISIT ADMIN (UNCHANGED + SAFE)
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

    def province_filter_kwargs(self, request):
        return {"facilityfk__districtfk__provincefk": user_province(request)}

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "facilityfk" and not request.user.is_superuser:
            Facility = db_field.remote_field.model
            prov = user_province(request)
            kwargs["queryset"] = Facility.objects.filter(
                districtfk__provincefk=prov
            ) if prov else Facility.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    class Media:
        js = ("mentorship/js/prefill_staff_facility.js",)

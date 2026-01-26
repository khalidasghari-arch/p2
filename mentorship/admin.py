import re
from django.contrib import admin
from .models import (
    ThematicMentorship, MentorshipTopics,
    Mentorshipvisit, Mentorshipdetails, Staff
)
from hiva.admin_utils import ProvinceRestrictedAdminMixin, user_province

@admin.register(ThematicMentorship)
class ThematicMentorshipAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "shortname")
    search_fields = ("name", "shortname")

@admin.register(MentorshipTopics)
class MentorshipTopicsAdmin(admin.ModelAdmin):
    list_display = ("id", "thematicfk", "name", "nameeng", "namedari", "namepashto")
    list_filter = ("thematicfk",)
    search_fields = ("name", "shortname", "namedari", "namepashto", "nameeng")

@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ("id", "hfname", "tazkiranumber", "firstname", "lastname", "position", "gender", "status")
    list_filter = ("hfname", "status", "position")
    search_fields = ("firstname", "lastname", "tazkiranumber")

    # ---------- helpers ----------
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
        # Example: /admin/mentorship/mentorshipvisit/2/change/
        m = re.search(r"/admin/mentorship/mentorshipvisit/(\d+)/change/?", ref)
        if not m:
            return None

        visit_id = m.group(1)
        try:
            visit = Mentorshipvisit.objects.only("id", "facilityfk_id").get(pk=visit_id)
            return str(visit.facilityfk_id)
        except Mentorshipvisit.DoesNotExist:
            return None

    # ---------- restrict Staff list to user's province ----------
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs

        prov = user_province(request)
        if prov is None:
            return qs.none()

        return qs.filter(hfname__districtfk__provincefk=prov)

    # ---------- prefill facility on add form ----------
    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        facility_id = self._facility_id_from_popup_context(request)
        if facility_id:
            initial["hfname"] = facility_id
        return initial

    # ---------- restrict facility dropdown ----------
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "hfname" and not request.user.is_superuser:
            Facility = db_field.remote_field.model  # hiva.Facility

            facility_id = self._facility_id_from_popup_context(request)

            # Case 1: opened from mentorship popup -> ONLY THAT facility + selected
            if facility_id:
                kwargs["queryset"] = Facility.objects.filter(pk=facility_id)
                field = super().formfield_for_foreignkey(db_field, request, **kwargs)
                field.initial = facility_id  # <-- IMPORTANT (so it shows selected)
                return field

            # Case 2: normal Staff add/edit -> province facilities only
            prov = user_province(request)
            if prov is None:
                kwargs["queryset"] = Facility.objects.none()
            else:
                kwargs["queryset"] = Facility.objects.filter(
                    districtfk__provincefk=prov
                ).order_by("name")

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

class MentorshipdetailsInline(admin.TabularInline):
    model = Mentorshipdetails
    extra = 0  # HQIP-style: show inline only after header saved

    def get_extra(self, request, obj=None, **kwargs):
        return 1 if obj else 0

    def has_add_permission(self, request, obj=None):
        # Prevent adding details before the header exists
        if obj is None:
            return False
        return super().has_add_permission(request, obj=obj)

    def get_formset(self, request, obj=None, **kwargs):
        # Stash parent object so formfield_for_foreignkey can use it
        request._mentorship_parent_obj = obj
        return super().get_formset(request, obj, **kwargs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        parent_obj = getattr(request, "_mentorship_parent_obj", None)

        # Filter mentees based on the selected facility on Mentorshipvisit (parent)
        if db_field.name == "menteename":
            if parent_obj:
                kwargs["queryset"] = Staff.objects.filter(
                    hfname=parent_obj.facilityfk
                ).order_by("firstname", "lastname")
            else:
                kwargs["queryset"] = Staff.objects.none()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

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
        return {"facilityfk__districtfk__provincefk": user_province(request)}

    # Restrict the facility dropdown itself (Add/Edit forms)
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "facilityfk" and not request.user.is_superuser:
            prov = user_province(request)
            Facility = db_field.remote_field.model  # hiva.Facility

            if prov is None:
                kwargs["queryset"] = Facility.objects.none()
            else:
                kwargs["queryset"] = Facility.objects.filter(
                    districtfk__provincefk=prov
                ).order_by("name")

        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    class Media:
            js = ("mentorship/js/prefill_staff_facility.js",)
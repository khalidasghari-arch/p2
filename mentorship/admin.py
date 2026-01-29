import re
from django.contrib import admin
from django import forms
from django.core.exceptions import ValidationError
from .models import (
    ThematicMentorship, MentorshipTopics,
    Mentorshipvisit, Mentorshipdetails, Staff
)
from hiva.admin_utils import ProvinceRestrictedAdminMixin, user_province
from django.urls import path, reverse
from django.http import JsonResponse

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

class MentorshipdetailsInlineForm(forms.ModelForm):
    class Meta:
        model = Mentorshipdetails
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Default: no topics until we know thematic
        self.fields["topicname"].queryset = MentorshipTopics.objects.none()

        thematic_id = None

        # 1) If user is submitting/changing values, get thematic from POST
        # Inline field name is like: <prefix>-thematicname
        if self.is_bound:
            thematic_id = self.data.get(f"{self.prefix}-thematicname") or None

        # 2) If editing existing row, get thematic from saved instance
        if not thematic_id and getattr(self.instance, "thematicname_id", None):
            thematic_id = self.instance.thematicname_id

        # Apply filter
        if thematic_id:
            self.fields["topicname"].queryset = MentorshipTopics.objects.filter(
                thematicfk_id=thematic_id
            ).order_by("shortname", "name")

    def clean(self):
        cleaned = super().clean()

        # Enforce only ONE of LS/PC/MC
        selected = sum([
            bool(cleaned.get("ls")),
            bool(cleaned.get("pc")),
            bool(cleaned.get("mc")),
        ])
        if selected > 1:
            raise ValidationError("Only ONE of LS, PC, or MC can be selected.")

        # Optional safety: if topic is selected, ensure it matches thematic
        thematic = cleaned.get("thematicname")
        topic = cleaned.get("topicname")
        if thematic and topic and topic.thematicfk_id != thematic.id:
            raise ValidationError("Selected topic does not match the selected thematic area.")

        return cleaned
    
# =====================================================
# INLINE – mentee by facility, topic by thematic, assessor by province
# =====================================================

class MentorshipdetailsInline(admin.TabularInline):
    model = Mentorshipdetails
    form = MentorshipdetailsInlineForm
    extra = 0  # HQIP-style: show inline only after header saved

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

        # Mentee: only staff from parent facility
        if db_field.name == "menteename":
            if parent_obj:
                kwargs["queryset"] = Staff.objects.filter(
                    hfname=parent_obj.facilityfk
                ).order_by("firstname", "lastname")
            else:
                kwargs["queryset"] = Staff.objects.none()

        # Mentor (Assessor): restrict by user province
        if db_field.name == "mentor" and not request.user.is_superuser:
            Assessor = db_field.remote_field.model  # hiva.Assessor
            prov = user_province(request)

            # IMPORTANT: adjust this line if your Assessor uses provincefk, etc.
            kwargs["queryset"] = Assessor.objects.filter(province=prov) if prov else Assessor.objects.none()

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

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "topics-by-thematic/",
                self.admin_site.admin_view(self.topics_by_thematic),
                name="mentorship_topics_by_thematic",
            )
        ]
        return custom + urls

    def topics_by_thematic(self, request):
        thematic_id = request.GET.get("thematic_id")
        if not thematic_id:
            return JsonResponse({"results": []})

        qs = MentorshipTopics.objects.filter(thematicfk_id=thematic_id).order_by("shortname", "name")

        results = []
        for t in qs:
            label = f"{t.shortname} - {t.name}" if t.shortname else t.name
            results.append({"id": t.id, "label": label})

        return JsonResponse({"results": results})

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        """
        Pass absolute endpoint URL to JS.
        """
        extra_context = extra_context or {}
        extra_context["TOPICS_ENDPOINT_URL"] = reverse("admin:mentorship_topics_by_thematic")
        return super().changeform_view(request, object_id, form_url, extra_context=extra_context)

    class Media:
        js = (
            "mentorship/js/prefill_staff_facility.js",
            "mentorship/js/topic_refresh.js",
        )
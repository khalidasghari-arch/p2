from django.contrib import admin
from .models import (
    ThematicMentorship, MentorshipTopics,
    Mentorshipvisit, Mentorshipdetails, Staff
)
from hiva.admin_utils import ProvinceRestrictedAdminMixin, user_province

@admin.register(ThematicMentorship)
class ThematicMentorshipAdmin(admin.ModelAdmin):
    list_display= ("id", "name", "shortname")
    search_fields = ("name", "shortname")


@admin.register(MentorshipTopics)
class MentorshipTopicsAdmin(admin.ModelAdmin):
    list_display = ("id", "thematicfk", "name","nameeng", "namedari", "namepashto")
    list_filter = ("thematicfk",)
    search_fields = ("name", "shortname", "namedari", "namepashto", "nameeng")


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ("id", "hfname", "tazkiranumber", "firstname", "lastname", "position", "gender","status")
    list_filter = ("hfname", "status", "position")
    search_fields = ("firstname", "lastname", "tazkiranumber")


class MentorshipdetailsInline(admin.TabularInline):
    model = Mentorshipdetails
    extra = 0  # start with 0; we’ll set it dynamically
    autocomplete_fields = ("menteename", "mentor", "thematicname", "topicname")

    # Make it “HQIP-like”: details appear only after header saved
    def get_extra(self, request, obj=None, **kwargs):
        return 1 if obj else 0

    def has_add_permission(self, request, obj):
        # prevent adding details before the header exists
        if obj is None:
            return False
        return super().has_add_permission(request, obj)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Filter mentees based on the selected facility on Mentorshipvisit (parent).
        Also (optional) filter topics based on thematic in the same row (needs JS for perfect UX),
        but we at least filter topics if request contains a thematic.
        """
        parent_obj = getattr(request, "_mentorship_parent_obj", None)

        if db_field.name == "menteename":
            qs = Staff.objects.all()
            if parent_obj:
                qs = qs.filter(hfname=parent_obj.facilityfk).order_by("firstname", "lastname")
            kwargs["queryset"] = qs

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_formset(self, request, obj=None, **kwargs):
        # stash parent object so formfield_for_foreignkey can use it
        request._mentorship_parent_obj = obj
        return super().get_formset(request, obj, **kwargs)


@admin.register(Mentorshipvisit)
class MentorshipvisitAdmin(ProvinceRestrictedAdminMixin, admin.ModelAdmin):
    list_display = ("id", "facilityfk", "visitdate", "visitround", "mentorshipstarttime", "mentorshipendtime")
    list_filter = ("visitdate", "facilityfk", )
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
        return {"facilityfk__districtfk__provincefk": request.user.profile.province}

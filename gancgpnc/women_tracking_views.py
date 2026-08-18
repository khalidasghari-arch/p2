# ============================================================
# GANC / PNC WOMEN TRACKING VIEW
# ============================================================

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.shortcuts import render

from .models import (
    Gancohort,
    Gancenrollment,
)

from .women_tracking_services import (
    get_women_tracking_queryset,
    get_women_tracking_summary,
    build_women_tracking_rows,
)


@staff_member_required
def women_tracking_dashboard(request):

    # ========================================================
    # BASE POPULATION
    # ========================================================

    enrollments = Gancenrollment.objects.select_related(
        "cohortname",
        "cohortname__facility",
        "cohortname__facility__districtfk",
        "cohortname__facility__districtfk__provincefk",
    )

    # ========================================================
    # FILTER PARAMETERS
    # ========================================================

    province_id = request.GET.get(
        "province",
        ""
    )

    district_id = request.GET.get(
        "district",
        ""
    )

    facility_id = request.GET.get(
        "facility",
        ""
    )

    cohort_id = request.GET.get(
        "cohort",
        ""
    )

    tracking_status = request.GET.get(
        "tracking_status",
        ""
    )

    next_stage = request.GET.get(
        "next_stage",
        ""
    )

    search = request.GET.get(
        "search",
        ""
    ).strip()

    # ========================================================
    # LOCATION FILTERS
    # ========================================================

    if province_id:
        enrollments = enrollments.filter(
            cohortname__facility__districtfk__provincefk_id=province_id
        )

    if district_id:
        enrollments = enrollments.filter(
            cohortname__facility__districtfk_id=district_id
        )

    if facility_id:
        enrollments = enrollments.filter(
            cohortname__facility_id=facility_id
        )

    if cohort_id:
        enrollments = enrollments.filter(
            cohortname_id=cohort_id
        )

    # ========================================================
    # SEARCH
    # ========================================================

    if search:

        search_query = (
            Q(name__icontains=search)
            | Q(fathername__icontains=search)
            | Q(contactnumber__icontains=search)
        )

        # Enrollment ID is numeric, therefore only search it
        # when the entered value is numeric.
        if search.isdigit():

            search_query |= Q(
                enrollmentid=int(search)
            )

        enrollments = enrollments.filter(
            search_query
        )

    # ========================================================
    # BUILD TRACKING QUERYSET
    # ========================================================

    tracking_queryset = get_women_tracking_queryset(
        enrollments
    )

    # ========================================================
    # TRACKING STATUS FILTER
    # ========================================================

    if tracking_status:

        tracking_queryset = tracking_queryset.filter(
            tracking_status=tracking_status
        )

    # ========================================================
    # NEXT STAGE FILTER
    # ========================================================

    if next_stage:

        tracking_queryset = tracking_queryset.filter(
            next_stage=next_stage
        )

    # ========================================================
    # ORDER
    # ========================================================

    tracking_queryset = tracking_queryset.order_by(
        "cohortname__cohortname",
        "enrollmentid",
        "name",
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    summary = get_women_tracking_summary(
        tracking_queryset
    )

    # ========================================================
    # ROWS
    # ========================================================

    women = build_women_tracking_rows(
        tracking_queryset
    )

    # ========================================================
    # FILTER OPTIONS
    # ========================================================

    cohorts = Gancohort.objects.select_related(
        "facility",
        "facility__districtfk",
        "facility__districtfk__provincefk",
    ).order_by(
        "cohortname"
    )

    # ========================================================
    # CONTEXT
    # ========================================================

    context = {

        "title": "Women Continuum Tracking",

        "women": women,

        "summary": summary,

        "cohorts": cohorts,

        # Current filter selections

        "selected_province": province_id,
        "selected_district": district_id,
        "selected_facility": facility_id,
        "selected_cohort": cohort_id,

        "selected_tracking_status": tracking_status,
        "selected_next_stage": next_stage,

        "search_value": search,
    }

    return render(
        request,
        "gancgpnc/women_tracking.html",
        context,
    )
# ============================================================
# GANC / PNC STRATEGIC DASHBOARD VIEWS
# ============================================================

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404
from django.shortcuts import render

from .models import Gancohort

from .dashboard_services import (
    get_base_enrollments,
    restrict_enrollments_to_user_province,
    apply_dashboard_filters,
    get_dashboard_summary,
    get_continuum_data,
    get_followup_summary,
    get_cohort_performance,
    get_filter_options,
    get_anc_quality_summary,
    get_delivery_summary,
    get_pnc_summary,
)


# ============================================================
# USER PROVINCE
# ============================================================

def get_user_province(request):

    if request.user.is_superuser:
        return None

    province = getattr(
        request.user,
        "province",
        None,
    )

    if province is not None:
        return province

    profile = getattr(
        request.user,
        "profile",
        None,
    )

    if profile is not None:

        province = getattr(
            profile,
            "province",
            None,
        )

        if province is not None:
            return province

    return None


# ============================================================
# MAIN DASHBOARD
# ============================================================

@staff_member_required
def ganc_dashboard(request):

    if not getattr(
        settings,
        "GANC_DASHBOARD_ENABLED",
        True,
    ):
        raise Http404(
            "GANC/PNC Dashboard is disabled."
        )

    user_province = get_user_province(
        request
    )

    province_id = (
        request.GET.get(
            "province"
        )
        or None
    )

    district_id = (
        request.GET.get(
            "district"
        )
        or None
    )

    facility_id = (
        request.GET.get(
            "facility"
        )
        or None
    )

    cohort_id = (
        request.GET.get(
            "cohort"
        )
        or None
    )

    cohort_status = (
        request.GET.get(
            "cohort_status"
        )
        or None
    )

    # ========================================================
    # MASTER POPULATION
    # ========================================================

    enrollments = (
        get_base_enrollments()
    )

    enrollments = (
        restrict_enrollments_to_user_province(
            queryset=enrollments,
            province=user_province,
            is_superuser=(
                request.user.is_superuser
            ),
        )
    )

    enrollments = (
        apply_dashboard_filters(
            queryset=enrollments,
            province_id=province_id,
            district_id=district_id,
            facility_id=facility_id,
            cohort_id=cohort_id,
            cohort_status=cohort_status,
        )
    )

    # ========================================================
    # ANALYSIS
    # ========================================================

    summary = (
        get_dashboard_summary(
            enrollments
        )
    )

    continuum = (
        get_continuum_data(
            enrollments
        )
    )

    followup = (
        get_followup_summary(
            enrollments
        )
    )

    cohort_performance = (
        get_cohort_performance(
            enrollments
        )
    )

    anc_quality = (
        get_anc_quality_summary(
            enrollments
        )
    )

    delivery_summary = (
        get_delivery_summary(
            enrollments
        )
    )

    pnc_summary = (
        get_pnc_summary(
            enrollments
        )
    )

    # ========================================================
    # FILTER OPTIONS
    # ========================================================

    filter_options = (
        get_filter_options(
            province=user_province,
            is_superuser=(
                request.user.is_superuser
            ),
            province_id=province_id,
            district_id=district_id,
            facility_id=facility_id,
        )
    )

    cohort_status_choices = (
        Gancohort.STATUS_CHOICES
    )

    selected_filters = {
        "province": str(
            province_id or ""
        ),

        "district": str(
            district_id or ""
        ),

        "facility": str(
            facility_id or ""
        ),

        "cohort": str(
            cohort_id or ""
        ),

        "cohort_status": str(
            cohort_status or ""
        ),
    }

    # ========================================================
    # CHART DATA
    # ========================================================

    continuum_labels = [
        item["label"]
        for item in continuum
    ]

    continuum_counts = [
        item["count"]
        for item in continuum
    ]

    breastfeeding_labels = [
        "Delivery",
        "PNC First",
        "PNC Second",
    ]

    breastfeeding_values = [
        delivery_summary[
            "early_breastfeeding_pct"
        ],

        pnc_summary[
            "pnc1"
        ][
            "exclusive_breastfeeding_pct"
        ],

        pnc_summary[
            "pnc2"
        ][
            "exclusive_breastfeeding_pct"
        ],
    ]

    # ========================================================
    # CONTEXT
    # ========================================================

    context = {
        "title": (
            "GANC/PNC Continuum of Care Dashboard"
        ),

        "summary": summary,

        "continuum": continuum,

        "followup": followup,

        "cohort_performance": (
            cohort_performance
        ),

        "anc_quality": (
            anc_quality
        ),

        "delivery_summary": (
            delivery_summary
        ),

        "pnc_summary": (
            pnc_summary
        ),

        "continuum_labels": (
            continuum_labels
        ),

        "continuum_counts": (
            continuum_counts
        ),

        "breastfeeding_labels": (
            breastfeeding_labels
        ),

        "breastfeeding_values": (
            breastfeeding_values
        ),

        "province_options": (
            filter_options[
                "province_options"
            ]
        ),

        "district_options": (
            filter_options[
                "district_options"
            ]
        ),

        "facility_options": (
            filter_options[
                "facility_options"
            ]
        ),

        "cohort_options": (
            filter_options[
                "cohort_options"
            ]
        ),

        "cohort_status_choices": (
            cohort_status_choices
        ),

        "selected_filters": (
            selected_filters
        ),

        "user_province": (
            user_province
        ),

        "is_superuser": (
            request.user.is_superuser
        ),
    }

    return render(
        request,
        "gancgpnc/dashboard.html",
        context,
    )
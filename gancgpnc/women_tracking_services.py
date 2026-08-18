# ============================================================
# GANC / PNC WOMEN TRACKING SERVICE
# ============================================================

from django.db.models import Exists, OuterRef, Case, When, Value, CharField

from .models import (
    Gancenrollment,
    Gancfirstsession,
    Gancsecondsession,
    Gancthirdsession,
    Gancfouthsession,
    Gancdelivery,
    GroupPncfirstSession,
    GroupPncsecondSession,
)


def get_women_tracking_queryset(enrollments):
    """
    Read-only continuum-of-care tracking.

    One row = one enrolled woman.

    Continuum:
    Enrollment
        -> ANC 1
        -> ANC 2
        -> ANC 3
        -> ANC 4
        -> Delivery
        -> PNC 1
        -> PNC 2
    """

    # ========================================================
    # CHECK WHETHER EACH STAGE EXISTS
    # ========================================================

    anc1_subquery = Gancfirstsession.objects.filter(
        registerid_id=OuterRef("pk")
    )

    anc2_subquery = Gancsecondsession.objects.filter(
        registerid_id=OuterRef("pk")
    )

    anc3_subquery = Gancthirdsession.objects.filter(
        registerid_id=OuterRef("pk")
    )

    anc4_subquery = Gancfouthsession.objects.filter(
        registerid_id=OuterRef("pk")
    )

    delivery_subquery = Gancdelivery.objects.filter(
        registerid_id=OuterRef("pk")
    )

    pnc1_subquery = GroupPncfirstSession.objects.filter(
        registerid_id=OuterRef("pk")
    )

    pnc2_subquery = GroupPncsecondSession.objects.filter(
        registerid_id=OuterRef("pk")
    )

    # ========================================================
    # ANNOTATE EACH ENROLLED WOMAN
    # ========================================================

    queryset = enrollments.annotate(
        has_anc1=Exists(anc1_subquery),
        has_anc2=Exists(anc2_subquery),
        has_anc3=Exists(anc3_subquery),
        has_anc4=Exists(anc4_subquery),
        has_delivery=Exists(delivery_subquery),
        has_pnc1=Exists(pnc1_subquery),
        has_pnc2=Exists(pnc2_subquery),
    )

    # ========================================================
    # LAST COMPLETED STAGE
    # ========================================================

    queryset = queryset.annotate(
        last_stage=Case(

            When(
                has_pnc2=True,
                then=Value("PNC SECOND")
            ),

            When(
                has_pnc1=True,
                then=Value("PNC FIRST")
            ),

            When(
                has_delivery=True,
                then=Value("DELIVERY")
            ),

            When(
                has_anc4=True,
                then=Value("ANC FOURTH")
            ),

            When(
                has_anc3=True,
                then=Value("ANC THIRD")
            ),

            When(
                has_anc2=True,
                then=Value("ANC SECOND")
            ),

            When(
                has_anc1=True,
                then=Value("ANC FIRST")
            ),

            default=Value("ENROLLMENT"),

            output_field=CharField(),
        )
    )

    # ========================================================
    # NEXT EXPECTED STAGE
    # ========================================================

    queryset = queryset.annotate(
        next_stage=Case(

            When(
                has_pnc2=True,
                then=Value("COMPLETED")
            ),

            When(
                has_pnc1=True,
                then=Value("PNC SECOND")
            ),

            When(
                has_delivery=True,
                then=Value("PNC FIRST")
            ),

            When(
                has_anc4=True,
                then=Value("DELIVERY")
            ),

            When(
                has_anc3=True,
                then=Value("ANC FOURTH")
            ),

            When(
                has_anc2=True,
                then=Value("ANC THIRD")
            ),

            When(
                has_anc1=True,
                then=Value("ANC SECOND")
            ),

            default=Value("ANC FIRST"),

            output_field=CharField(),
        )
    )

    # ========================================================
    # TRACKING STATUS
    # ========================================================

    queryset = queryset.annotate(
        tracking_status=Case(

            When(
                has_pnc2=True,
                then=Value("COMPLETED")
            ),

            When(
                has_pnc1=True,
                then=Value("IN PROGRESS")
            ),

            When(
                has_delivery=True,
                then=Value("IN PROGRESS")
            ),

            When(
                has_anc4=True,
                then=Value("IN PROGRESS")
            ),

            When(
                has_anc3=True,
                then=Value("IN PROGRESS")
            ),

            When(
                has_anc2=True,
                then=Value("IN PROGRESS")
            ),

            When(
                has_anc1=True,
                then=Value("IN PROGRESS")
            ),

            default=Value("FOLLOW-UP REQUIRED"),

            output_field=CharField(),
        )
    )

    return queryset


# ============================================================
# WOMEN TRACKING SUMMARY
# ============================================================

def get_women_tracking_summary(queryset):
    """
    Summary KPI values for the Women Tracking page.
    """

    total = queryset.count()

    completed = queryset.filter(
        tracking_status="COMPLETED"
    ).count()

    in_progress = queryset.filter(
        tracking_status="IN PROGRESS"
    ).count()

    followup_required = queryset.filter(
        tracking_status="FOLLOW-UP REQUIRED"
    ).count()

    missing_anc1 = queryset.filter(
        has_anc1=False
    ).count()

    missing_anc2 = queryset.filter(
        has_anc1=True,
        has_anc2=False
    ).count()

    missing_anc3 = queryset.filter(
        has_anc2=True,
        has_anc3=False
    ).count()

    missing_anc4 = queryset.filter(
        has_anc3=True,
        has_anc4=False
    ).count()

    missing_delivery = queryset.filter(
        has_anc4=True,
        has_delivery=False
    ).count()

    missing_pnc1 = queryset.filter(
        has_delivery=True,
        has_pnc1=False
    ).count()

    missing_pnc2 = queryset.filter(
        has_pnc1=True,
        has_pnc2=False
    ).count()

    return {
        "total": total,
        "completed": completed,
        "in_progress": in_progress,
        "followup_required": followup_required,

        "missing_anc1": missing_anc1,
        "missing_anc2": missing_anc2,
        "missing_anc3": missing_anc3,
        "missing_anc4": missing_anc4,
        "missing_delivery": missing_delivery,
        "missing_pnc1": missing_pnc1,
        "missing_pnc2": missing_pnc2,
    }


# ============================================================
# CONVERT QUERYSET TO DASHBOARD ROWS
# ============================================================

def build_women_tracking_rows(queryset):

    rows = []

    queryset = queryset.select_related(
        "cohortname",
        "cohortname__facility",
        "cohortname__facility__districtfk",
        "cohortname__facility__districtfk__provincefk",
    )

    for woman in queryset:

        cohort = woman.cohortname

        facility = (
            cohort.facility
            if cohort
            else None
        )

        district = (
            facility.districtfk
            if facility
            else None
        )

        province = (
            district.provincefk
            if district
            else None
        )

        rows.append({

            "id": woman.pk,

            "register_number": (
                woman.enrollmentid
                if woman.enrollmentid is not None
                else ""
            ),

            "woman_name": (
                woman.name or ""
            ),

            "father_name": (
                woman.fathername or ""
            ),

            "contact_number": (
                woman.contactnumber or ""
            ),

            "cohort": (
                str(cohort)
                if cohort
                else ""
            ),

            "facility": (
                str(facility)
                if facility
                else ""
            ),

            "district": (
                str(district)
                if district
                else ""
            ),

            "province": (
                str(province)
                if province
                else ""
            ),

            "anc1": woman.has_anc1,
            "anc2": woman.has_anc2,
            "anc3": woman.has_anc3,
            "anc4": woman.has_anc4,

            "delivery": woman.has_delivery,

            "pnc1": woman.has_pnc1,
            "pnc2": woman.has_pnc2,

            "last_stage": woman.last_stage,

            "next_stage": woman.next_stage,

            "tracking_status": woman.tracking_status,
        })

    return rows
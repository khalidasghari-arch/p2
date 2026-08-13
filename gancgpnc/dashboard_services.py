# ============================================================
# GANC / PNC STRATEGIC DASHBOARD SERVICES
# ============================================================

from django.db.models import Avg, Count, Sum

from .models import (
    Gancohort,
    Gancenrollment,
    Gancfirstsession,
    Gancsecondsession,
    Gancthirdsession,
    Gancfouthsession,
    Gancdelivery,
    GroupPncfirstSession,
    GroupPncsecondSession,
)


# ============================================================
# GENERAL HELPERS
# ============================================================

def percentage(numerator, denominator):
    if not denominator:
        return 0.0

    return round(
        (numerator / denominator) * 100,
        1,
    )


def unique_register_count(queryset):
    return (
        queryset
        .exclude(registerid_id__isnull=True)
        .values("registerid_id")
        .distinct()
        .count()
    )


def unique_register_ids(queryset):
    return set(
        queryset
        .exclude(registerid_id__isnull=True)
        .values_list(
            "registerid_id",
            flat=True,
        )
        .distinct()
    )


def safe_average(queryset, field_name):
    try:
        field = queryset.model._meta.get_field(
            field_name
        )
    except Exception:
        return 0

    numeric_types = {
        "IntegerField",
        "PositiveIntegerField",
        "PositiveSmallIntegerField",
        "SmallIntegerField",
        "BigIntegerField",
        "FloatField",
        "DecimalField",
    }

    if field.get_internal_type() not in numeric_types:
        return 0

    value = queryset.aggregate(
        avg_value=Avg(field_name)
    )["avg_value"]

    if value is None:
        return 0

    return round(
        float(value),
        1,
    )


def safe_sum(queryset, field_name):
    try:
        field = queryset.model._meta.get_field(
            field_name
        )
    except Exception:
        return 0

    numeric_types = {
        "IntegerField",
        "PositiveIntegerField",
        "PositiveSmallIntegerField",
        "SmallIntegerField",
        "BigIntegerField",
        "FloatField",
        "DecimalField",
    }

    if field.get_internal_type() not in numeric_types:
        return 0

    value = queryset.aggregate(
        total=Sum(field_name)
    )["total"]

    return value or 0


def positive_unique_count(
    queryset,
    field_name,
):
    """
    Handles BooleanField and legacy Yes/No text fields.
    """

    try:
        field = queryset.model._meta.get_field(
            field_name
        )
    except Exception:
        return 0

    field_type = field.get_internal_type()

    if field_type in {
        "BooleanField",
        "NullBooleanField",
    }:
        filtered = queryset.filter(
            **{
                field_name: True
            }
        )

    else:
        filtered = queryset.filter(
            **{
                f"{field_name}__in": [
                    "Y",
                    "Yes",
                    "YES",
                    "yes",
                    "TRUE",
                    "True",
                    "true",
                    "1",
                ]
            }
        )

    return unique_register_count(
        filtered
    )


def nonempty_unique_count(
    queryset,
    field_name,
):
    return unique_register_count(
        queryset
        .exclude(
            **{
                f"{field_name}__isnull": True
            }
        )
        .exclude(
            **{
                field_name: ""
            }
        )
    )


# ============================================================
# MASTER ENROLLMENT POPULATION
# ============================================================

def get_base_enrollments():
    return (
        Gancenrollment.objects
        .select_related(
            "cohortname",
            "cohortname__facility",
            "cohortname__facility__districtfk",
            "cohortname__facility__districtfk__provincefk",
        )
        .all()
    )


# ============================================================
# USER PROVINCE RESTRICTION
# ============================================================

def restrict_enrollments_to_user_province(
    queryset,
    province=None,
    is_superuser=False,
):
    if is_superuser:
        return queryset

    if province is not None:
        queryset = queryset.filter(
            cohortname__facility__districtfk__provincefk=province
        )

    return queryset


# ============================================================
# GLOBAL FILTERS
# ============================================================

def apply_dashboard_filters(
    queryset,
    province_id=None,
    district_id=None,
    facility_id=None,
    cohort_id=None,
    cohort_status=None,
):
    if province_id:
        queryset = queryset.filter(
            cohortname__facility__districtfk__provincefk_id=province_id
        )

    if district_id:
        queryset = queryset.filter(
            cohortname__facility__districtfk_id=district_id
        )

    if facility_id:
        queryset = queryset.filter(
            cohortname__facility_id=facility_id
        )

    if cohort_id:
        queryset = queryset.filter(
            cohortname_id=cohort_id
        )

    if cohort_status:
        queryset = queryset.filter(
            cohortname__cohortstatus=cohort_status
        )

    return queryset.distinct()


# ============================================================
# SESSION QUERYSETS
# ============================================================

def get_session_querysets(enrollments):

    enrollment_ids = enrollments.values_list(
        "pk",
        flat=True,
    )

    return {
        "anc1": Gancfirstsession.objects.filter(
            registerid_id__in=enrollment_ids
        ),

        "anc2": Gancsecondsession.objects.filter(
            registerid_id__in=enrollment_ids
        ),

        "anc3": Gancthirdsession.objects.filter(
            registerid_id__in=enrollment_ids
        ),

        "anc4": Gancfouthsession.objects.filter(
            registerid_id__in=enrollment_ids
        ),

        "delivery": Gancdelivery.objects.filter(
            registerid_id__in=enrollment_ids
        ),

        "pnc1": GroupPncfirstSession.objects.filter(
            registerid_id__in=enrollment_ids
        ),

        "pnc2": GroupPncsecondSession.objects.filter(
            registerid_id__in=enrollment_ids
        ),
    }


# ============================================================
# EXECUTIVE SUMMARY
# ============================================================

def get_dashboard_summary(enrollments):

    sessions = get_session_querysets(
        enrollments
    )

    enrolled = (
        enrollments
        .values("pk")
        .distinct()
        .count()
    )

    anc1 = unique_register_count(
        sessions["anc1"]
    )

    anc2 = unique_register_count(
        sessions["anc2"]
    )

    anc3 = unique_register_count(
        sessions["anc3"]
    )

    anc4 = unique_register_count(
        sessions["anc4"]
    )

    delivery = unique_register_count(
        sessions["delivery"]
    )

    pnc1 = unique_register_count(
        sessions["pnc1"]
    )

    pnc2 = unique_register_count(
        sessions["pnc2"]
    )

    return {
        "enrolled": enrolled,
        "anc1": anc1,
        "anc2": anc2,
        "anc3": anc3,
        "anc4": anc4,
        "delivery": delivery,
        "pnc1": pnc1,
        "pnc2": pnc2,

        "anc1_pct": percentage(
            anc1,
            enrolled,
        ),

        "anc2_pct": percentage(
            anc2,
            enrolled,
        ),

        "anc3_pct": percentage(
            anc3,
            enrolled,
        ),

        "anc4_pct": percentage(
            anc4,
            enrolled,
        ),

        "delivery_pct": percentage(
            delivery,
            enrolled,
        ),

        "pnc1_pct": percentage(
            pnc1,
            enrolled,
        ),

        "pnc2_pct": percentage(
            pnc2,
            enrolled,
        ),

        "anc1_to_anc2": percentage(
            anc2,
            anc1,
        ),

        "anc2_to_anc3": percentage(
            anc3,
            anc2,
        ),

        "anc3_to_anc4": percentage(
            anc4,
            anc3,
        ),

        "anc1_to_anc4": percentage(
            anc4,
            anc1,
        ),

        "anc4_to_delivery": percentage(
            delivery,
            anc4,
        ),

        "delivery_to_pnc1": percentage(
            pnc1,
            delivery,
        ),

        "pnc1_to_pnc2": percentage(
            pnc2,
            pnc1,
        ),

        "full_continuum_completion": percentage(
            pnc2,
            enrolled,
        ),
    }


# ============================================================
# CONTINUUM
# ============================================================

def get_continuum_data(enrollments):

    summary = get_dashboard_summary(
        enrollments
    )

    stages = [
        {
            "label": "Enrollment",
            "count": summary["enrolled"],
        },
        {
            "label": "ANC First",
            "count": summary["anc1"],
        },
        {
            "label": "ANC Second",
            "count": summary["anc2"],
        },
        {
            "label": "ANC Third",
            "count": summary["anc3"],
        },
        {
            "label": "ANC Fourth",
            "count": summary["anc4"],
        },
        {
            "label": "Delivery",
            "count": summary["delivery"],
        },
        {
            "label": "PNC First",
            "count": summary["pnc1"],
        },
        {
            "label": "PNC Second",
            "count": summary["pnc2"],
        },
    ]

    enrolled = summary["enrolled"]
    previous = None

    for stage in stages:

        stage["enrollment_pct"] = percentage(
            stage["count"],
            enrolled,
        )

        if previous is None:
            stage["previous_stage_pct"] = 100.0

        else:
            stage["previous_stage_pct"] = percentage(
                stage["count"],
                previous,
            )

        previous = stage["count"]

    return stages


# ============================================================
# FOLLOW-UP
# ============================================================

def get_followup_summary(enrollments):

    sessions = get_session_querysets(
        enrollments
    )

    enrollment_ids = set(
        enrollments.values_list(
            "pk",
            flat=True,
        )
    )

    anc1_ids = unique_register_ids(
        sessions["anc1"]
    )

    anc2_ids = unique_register_ids(
        sessions["anc2"]
    )

    anc3_ids = unique_register_ids(
        sessions["anc3"]
    )

    anc4_ids = unique_register_ids(
        sessions["anc4"]
    )

    delivery_ids = unique_register_ids(
        sessions["delivery"]
    )

    pnc1_ids = unique_register_ids(
        sessions["pnc1"]
    )

    pnc2_ids = unique_register_ids(
        sessions["pnc2"]
    )

    return {
        "enrolled_missing_anc1": len(
            enrollment_ids - anc1_ids
        ),

        "anc1_missing_anc2": len(
            anc1_ids - anc2_ids
        ),

        "anc2_missing_anc3": len(
            anc2_ids - anc3_ids
        ),

        "anc3_missing_anc4": len(
            anc3_ids - anc4_ids
        ),

        "anc4_missing_delivery": len(
            anc4_ids - delivery_ids
        ),

        "delivery_missing_pnc1": len(
            delivery_ids - pnc1_ids
        ),

        "pnc1_missing_pnc2": len(
            pnc1_ids - pnc2_ids
        ),
    }


# ============================================================
# COHORT PERFORMANCE
# ============================================================

def get_cohort_performance(enrollments):

    cohort_ids = (
        enrollments
        .exclude(
            cohortname_id__isnull=True
        )
        .values_list(
            "cohortname_id",
            flat=True,
        )
        .distinct()
    )

    cohorts = (
        Gancohort.objects
        .filter(
            pk__in=cohort_ids
        )
        .select_related(
            "facility",
            "facility__districtfk",
            "facility__districtfk__provincefk",
        )
        .order_by(
            "facility__districtfk__provincefk__name",
            "facility__name",
            "cohortnumber",
            "cohortname",
        )
    )

    results = []

    for cohort in cohorts:

        cohort_enrollments = (
            enrollments.filter(
                cohortname_id=cohort.pk
            )
        )

        summary = get_dashboard_summary(
            cohort_enrollments
        )

        completion = summary[
            "full_continuum_completion"
        ]

        if completion >= 85:
            performance_status = "Excellent"

        elif completion >= 70:
            performance_status = "On Track"

        elif completion >= 50:
            performance_status = "Needs Attention"

        else:
            performance_status = "Critical"

        facility = getattr(
            cohort,
            "facility",
            None,
        )

        district = (
            getattr(
                facility,
                "districtfk",
                None,
            )
            if facility
            else None
        )

        province = (
            getattr(
                district,
                "provincefk",
                None,
            )
            if district
            else None
        )

        results.append({
            "cohort_id": cohort.pk,

            "cohort_name": (
                cohort.cohortname
            ),

            "cohort_number": (
                cohort.cohortnumber
            ),

            "cohort_status": (
                cohort.cohortstatus
            ),

            "target_size": (
                cohort.target_size or 0
            ),

            "facility": (
                getattr(
                    facility,
                    "name",
                    "",
                )
                if facility
                else ""
            ),

            "district": (
                getattr(
                    district,
                    "name",
                    "",
                )
                if district
                else ""
            ),

            "province": (
                getattr(
                    province,
                    "name",
                    "",
                )
                if province
                else ""
            ),

            "enrolled": summary["enrolled"],
            "anc1": summary["anc1"],
            "anc2": summary["anc2"],
            "anc3": summary["anc3"],
            "anc4": summary["anc4"],
            "delivery": summary["delivery"],
            "pnc1": summary["pnc1"],
            "pnc2": summary["pnc2"],

            "completion_pct": completion,

            "performance_status": (
                performance_status
            ),
        })

    return results


# ============================================================
# FILTER OPTIONS
# ============================================================

def get_filter_options(
    province=None,
    is_superuser=False,
    province_id=None,
    district_id=None,
    facility_id=None,
):

    cohorts = (
        Gancohort.objects
        .select_related(
            "facility",
            "facility__districtfk",
            "facility__districtfk__provincefk",
        )
        .all()
    )

    if (
        not is_superuser
        and province is not None
    ):
        cohorts = cohorts.filter(
            facility__districtfk__provincefk=province
        )

    province_options = (
        cohorts
        .values(
            "facility__districtfk__provincefk_id",
            "facility__districtfk__provincefk__name",
        )
        .exclude(
            facility__districtfk__provincefk_id__isnull=True
        )
        .distinct()
        .order_by(
            "facility__districtfk__provincefk__name"
        )
    )

    district_queryset = cohorts

    if province_id:
        district_queryset = (
            district_queryset.filter(
                facility__districtfk__provincefk_id=province_id
            )
        )

    district_options = (
        district_queryset
        .values(
            "facility__districtfk_id",
            "facility__districtfk__name",
        )
        .exclude(
            facility__districtfk_id__isnull=True
        )
        .distinct()
        .order_by(
            "facility__districtfk__name"
        )
    )

    facility_queryset = cohorts

    if province_id:
        facility_queryset = (
            facility_queryset.filter(
                facility__districtfk__provincefk_id=province_id
            )
        )

    if district_id:
        facility_queryset = (
            facility_queryset.filter(
                facility__districtfk_id=district_id
            )
        )

    facility_options = (
        facility_queryset
        .values(
            "facility_id",
            "facility__name",
        )
        .exclude(
            facility_id__isnull=True
        )
        .distinct()
        .order_by(
            "facility__name"
        )
    )

    cohort_queryset = cohorts

    if province_id:
        cohort_queryset = (
            cohort_queryset.filter(
                facility__districtfk__provincefk_id=province_id
            )
        )

    if district_id:
        cohort_queryset = (
            cohort_queryset.filter(
                facility__districtfk_id=district_id
            )
        )

    if facility_id:
        cohort_queryset = (
            cohort_queryset.filter(
                facility_id=facility_id
            )
        )

    cohort_options = (
        cohort_queryset.order_by(
            "cohortname"
        )
    )

    return {
        "province_options": (
            province_options
        ),

        "district_options": (
            district_options
        ),

        "facility_options": (
            facility_options
        ),

        "cohort_options": (
            cohort_options
        ),
    }


# ============================================================
# ANC QUALITY
# ============================================================

def get_anc_quality_summary(enrollments):

    sessions = get_session_querysets(
        enrollments
    )

    anc1 = sessions["anc1"]
    anc2 = sessions["anc2"]
    anc3 = sessions["anc3"]
    anc4 = sessions["anc4"]

    def common_metrics(queryset):

        women = unique_register_count(
            queryset
        )

        hypertension = (
            positive_unique_count(
                queryset,
                "dhypertension",
            )
        )

        hypertension_referred = (
            positive_unique_count(
                queryset,
                "rhypertensiontoMD",
            )
        )

        anemia = (
            positive_unique_count(
                queryset,
                "anemia",
            )
        )

        iron_folate = (
            positive_unique_count(
                queryset,
                "ironfolate",
            )
        )

        calcium_prescribed = (
            positive_unique_count(
                queryset,
                "pcalcium",
            )
        )

        mam = positive_unique_count(
            queryset,
            "dmam",
        )

        mam_referred = (
            positive_unique_count(
                queryset,
                "rmam",
            )
        )

        sam = positive_unique_count(
            queryset,
            "dsam",
        )

        sam_referred = (
            positive_unique_count(
                queryset,
                "rsam",
            )
        )

        urine_exam = (
            positive_unique_count(
                queryset,
                "urinexamcheck",
            )
        )

        proteinuria_referred = (
            positive_unique_count(
                queryset,
                "rpositivepuriatomd",
            )
        )

        tt_vaccine = (
            positive_unique_count(
                queryset,
                "ttvaccine",
            )
        )

        danger_sign = (
            positive_unique_count(
                queryset,
                "dangersign",
            )
        )

        return {
            "women": women,

            "hypertension": hypertension,

            "hypertension_pct": percentage(
                hypertension,
                women,
            ),

            "hypertension_referral_pct": percentage(
                hypertension_referred,
                hypertension,
            ),

            "anemia": anemia,

            "anemia_pct": percentage(
                anemia,
                women,
            ),

            "iron_folate_pct": percentage(
                iron_folate,
                women,
            ),

            "calcium_prescribed_pct": percentage(
                calcium_prescribed,
                women,
            ),

            "average_muac": safe_average(
                queryset,
                "muac",
            ),

            "mam": mam,

            "mam_referral_pct": percentage(
                mam_referred,
                mam,
            ),

            "sam": sam,

            "sam_referral_pct": percentage(
                sam_referred,
                sam,
            ),

            "urine_exam_pct": percentage(
                urine_exam,
                women,
            ),

            "proteinuria_referral_pct": percentage(
                proteinuria_referred,
                nonempty_unique_count(
                    queryset,
                    "urinexam",
                ),
            ),

            "tt_vaccine_pct": percentage(
                tt_vaccine,
                women,
            ),

            "danger_sign": danger_sign,
        }

    anc1_data = common_metrics(
        anc1
    )

    laboratory_exam = (
        positive_unique_count(
            anc1,
            "clabexm",
        )
    )

    anc1_data.update({
        "laboratory_exam": (
            laboratory_exam
        ),

        "laboratory_exam_pct": percentage(
            laboratory_exam,
            anc1_data["women"],
        ),

        "average_hemoglobin": safe_average(
            anc1,
            "hemoglobin",
        ),
    })

    anc2_data = common_metrics(
        anc2
    )

    mebendazole = (
        positive_unique_count(
            anc2,
            "mebendazole",
        )
    )

    anc2_data.update({
        "mebendazole": mebendazole,

        "mebendazole_pct": percentage(
            mebendazole,
            anc2_data["women"],
        ),
    })

    anc3_data = common_metrics(
        anc3
    )

    depression_screened_3 = (
        positive_unique_count(
            anc3,
            "antedepressionscreening",
        )
    )

    depression_diagnosed_3 = (
        positive_unique_count(
            anc3,
            "antedepressiondiagnosed",
        )
    )

    psychosocial_referral_3 = (
        positive_unique_count(
            anc3,
            "rpsychosocialcounselor",
        )
    )

    birth_planning_3 = (
        positive_unique_count(
            anc3,
            "birthplanningcounseling",
        )
    )

    anc3_data.update({
        "depression_screened": (
            depression_screened_3
        ),

        "depression_screened_pct": percentage(
            depression_screened_3,
            anc3_data["women"],
        ),

        "depression_diagnosed": (
            depression_diagnosed_3
        ),

        "psychosocial_referral": (
            psychosocial_referral_3
        ),

        "psychosocial_referral_pct": percentage(
            psychosocial_referral_3,
            depression_diagnosed_3,
        ),

        "birth_planning": (
            birth_planning_3
        ),

        "birth_planning_pct": percentage(
            birth_planning_3,
            anc3_data["women"],
        ),
    })

    anc4_data = common_metrics(
        anc4
    )

    depression_screened_4 = (
        positive_unique_count(
            anc4,
            "antedepressionscreening",
        )
    )

    depression_diagnosed_4 = (
        positive_unique_count(
            anc4,
            "antedepressiondiagnosed",
        )
    )

    psychosocial_referral_4 = (
        positive_unique_count(
            anc4,
            "rpsychosocialcounselor",
        )
    )

    birth_planning_4 = (
        positive_unique_count(
            anc4,
            "birthplanningcounseling",
        )
    )

    anc4_data.update({
        "depression_screened": (
            depression_screened_4
        ),

        "depression_screened_pct": percentage(
            depression_screened_4,
            anc4_data["women"],
        ),

        "depression_diagnosed": (
            depression_diagnosed_4
        ),

        "psychosocial_referral": (
            psychosocial_referral_4
        ),

        "psychosocial_referral_pct": percentage(
            psychosocial_referral_4,
            depression_diagnosed_4,
        ),

        "birth_planning": (
            birth_planning_4
        ),

        "birth_planning_pct": percentage(
            birth_planning_4,
            anc4_data["women"],
        ),
    })

    return {
        "anc1": anc1_data,
        "anc2": anc2_data,
        "anc3": anc3_data,
        "anc4": anc4_data,
    }


# ============================================================
# DELIVERY SUMMARY
# ============================================================

def get_delivery_summary(enrollments):

    deliveries = get_session_querysets(
        enrollments
    )["delivery"]

    delivery_women = (
        unique_register_count(
            deliveries
        )
    )

    immediate_uterotonic = (
        positive_unique_count(
            deliveries,
            "immediate_uterotonic_for_amtsl",
        )
    )

    maternal_complication = (
        nonempty_unique_count(
            deliveries,
            "types_of_complication",
        )
    )

    maternal_death = (
        positive_unique_count(
            deliveries,
            "maternal_death",
        )
    )

    total_newborn = safe_sum(
        deliveries,
        "number_of_newborn",
    )

    alive_newborn = safe_sum(
        deliveries,
        "number_of_alive_newborn",
    )

    newborn_death = safe_sum(
        deliveries,
        "number_of_newborn_death",
    )

    fresh_stillbirth = safe_sum(
        deliveries,
        "number_of_fresh_still_birth",
    )

    early_breastfeeding = (
        positive_unique_count(
            deliveries,
            "early_breastfeeding",
        )
    )

    vaccination = (
        positive_unique_count(
            deliveries,
            "newborn_vaccination_before_discharge",
        )
    )

    ppfp_counseling = (
        positive_unique_count(
            deliveries,
            "counseled_on_postpartum_fp_before_discharge",
        )
    )

    immediate_ppfp = (
        positive_unique_count(
            deliveries,
            "immediate_ppfp_before_discharge",
        )
    )

    place_distribution = list(
        deliveries
        .exclude(
            place_of_delivery__isnull=True
        )
        .exclude(
            place_of_delivery=""
        )
        .values(
            "place_of_delivery"
        )
        .annotate(
            total=Count(
                "registerid_id",
                distinct=True,
            )
        )
        .order_by("-total")
    )

    for row in place_distribution:
        row["pct"] = percentage(
            row["total"],
            delivery_women,
        )

    delivery_type_distribution = list(
        deliveries
        .exclude(
            type_of_delivery__isnull=True
        )
        .exclude(
            type_of_delivery=""
        )
        .values(
            "type_of_delivery"
        )
        .annotate(
            total=Count(
                "registerid_id",
                distinct=True,
            )
        )
        .order_by("-total")
    )

    for row in delivery_type_distribution:
        row["pct"] = percentage(
            row["total"],
            delivery_women,
        )

    ppfp_method_distribution = list(
        deliveries
        .exclude(
            ppfp_method_taken_before_discharge__isnull=True
        )
        .exclude(
            ppfp_method_taken_before_discharge=""
        )
        .values(
            "ppfp_method_taken_before_discharge"
        )
        .annotate(
            total=Count(
                "registerid_id",
                distinct=True,
            )
        )
        .order_by("-total")
    )

    for row in ppfp_method_distribution:
        row["pct"] = percentage(
            row["total"],
            immediate_ppfp,
        )

    return {
        "deliveries": delivery_women,

        "average_gestational_age": safe_average(
            deliveries,
            "gestational_age_at_delivery",
        ),

        "immediate_uterotonic": (
            immediate_uterotonic
        ),

        "immediate_uterotonic_pct": percentage(
            immediate_uterotonic,
            delivery_women,
        ),

        "maternal_complication": (
            maternal_complication
        ),

        "maternal_complication_pct": percentage(
            maternal_complication,
            delivery_women,
        ),

        "maternal_death": (
            maternal_death
        ),

        "maternal_death_pct": percentage(
            maternal_death,
            delivery_women,
        ),

        "total_newborn": total_newborn,
        "alive_newborn": alive_newborn,

        "alive_newborn_pct": percentage(
            alive_newborn,
            total_newborn,
        ),

        "newborn_death": newborn_death,

        "newborn_death_pct": percentage(
            newborn_death,
            total_newborn,
        ),

        "fresh_stillbirth": (
            fresh_stillbirth
        ),

        "fresh_stillbirth_pct": percentage(
            fresh_stillbirth,
            total_newborn,
        ),

        "early_breastfeeding": (
            early_breastfeeding
        ),

        "early_breastfeeding_pct": percentage(
            early_breastfeeding,
            delivery_women,
        ),

        "vaccination_before_discharge": (
            vaccination
        ),

        "vaccination_before_discharge_pct": percentage(
            vaccination,
            delivery_women,
        ),

        "ppfp_counseling": (
            ppfp_counseling
        ),

        "ppfp_counseling_pct": percentage(
            ppfp_counseling,
            delivery_women,
        ),

        "immediate_ppfp": (
            immediate_ppfp
        ),

        "immediate_ppfp_pct": percentage(
            immediate_ppfp,
            delivery_women,
        ),

        "place_distribution": (
            place_distribution
        ),

        "delivery_type_distribution": (
            delivery_type_distribution
        ),

        "ppfp_method_distribution": (
            ppfp_method_distribution
        ),
    }


# ============================================================
# PNC FIRST + SECOND SUMMARY
# ============================================================

def get_pnc_summary(enrollments):

    sessions = get_session_querysets(
        enrollments
    )

    pnc1 = sessions["pnc1"]
    pnc2 = sessions["pnc2"]

    # ========================================================
    # PNC FIRST
    # ========================================================

    pnc1_women = unique_register_count(
        pnc1
    )

    pnc1_hypertension = (
        positive_unique_count(
            pnc1,
            "diagnosed_with_hypertension",
        )
    )

    pnc1_hypertension_referral = (
        positive_unique_count(
            pnc1,
            "referred_hypertension_to_md",
        )
    )

    pnc1_anemia = (
        positive_unique_count(
            pnc1,
            "anemia",
        )
    )

    pnc1_mam = (
        positive_unique_count(
            pnc1,
            "diagnosed_with_mam",
        )
    )

    pnc1_mam_referral = (
        positive_unique_count(
            pnc1,
            "refer_mam_to_nutrition_counselor",
        )
    )

    pnc1_sam = (
        positive_unique_count(
            pnc1,
            "diagnosed_with_sam",
        )
    )

    pnc1_sam_referral = (
        positive_unique_count(
            pnc1,
            "refer_sam_to_higher_level",
        )
    )

    pnc1_maternal_danger_sign = (
        nonempty_unique_count(
            pnc1,
            "type_of_maternal_danger_sign",
        )
    )

    pnc1_newborn_danger_sign = (
        nonempty_unique_count(
            pnc1,
            "type_of_newborn_danger_sign",
        )
    )

    pnc1_newborn_death = (
        positive_unique_count(
            pnc1,
            "newborn_death",
        )
    )

    pnc1_maternal_death = (
        positive_unique_count(
            pnc1,
            "maternal_death",
        )
    )

    pnc1_newborn_vaccination = (
        positive_unique_count(
            pnc1,
            "newborn_vaccination_completed",
        )
    )

    pnc1_exclusive_bf = (
        positive_unique_count(
            pnc1,
            "exclusive_breast_feeding",
        )
    )

    pnc1_ppfp_chosen = (
        positive_unique_count(
            pnc1,
            "chosen_ppfp_method",
        )
    )

    # ========================================================
    # PNC SECOND
    # ========================================================

    pnc2_women = unique_register_count(
        pnc2
    )

    pnc2_hypertension = (
        positive_unique_count(
            pnc2,
            "dhypertension",
        )
    )

    pnc2_hypertension_referral = (
        positive_unique_count(
            pnc2,
            "rhypertensiontomd",
        )
    )

    pnc2_anemia = (
        positive_unique_count(
            pnc2,
            "anemia",
        )
    )

    pnc2_mam = (
        positive_unique_count(
            pnc2,
            "dmam",
        )
    )

    pnc2_mam_referral = (
        positive_unique_count(
            pnc2,
            "rmam",
        )
    )

    pnc2_sam = (
        positive_unique_count(
            pnc2,
            "dsam",
        )
    )

    pnc2_sam_referral = (
        positive_unique_count(
            pnc2,
            "rsam",
        )
    )

    pnc2_depression = (
        positive_unique_count(
            pnc2,
            "postnataldepressiondiagnosed",
        )
    )

    pnc2_psychosocial_referral = (
        positive_unique_count(
            pnc2,
            "rpsychosocialcounselor",
        )
    )

    pnc2_maternal_danger_sign = (
        nonempty_unique_count(
            pnc2,
            "typeofmaternaldangersign",
        )
    )

    pnc2_newborn_danger_sign = (
        nonempty_unique_count(
            pnc2,
            "typeofnewborndangersign",
        )
    )

    pnc2_newborn_death = (
        positive_unique_count(
            pnc2,
            "newborndeath",
        )
    )

    pnc2_maternal_death = (
        positive_unique_count(
            pnc2,
            "maternaldeath",
        )
    )

    pnc2_newborn_vaccination = (
        positive_unique_count(
            pnc2,
            "newbornvaccinationcompleted",
        )
    )

    pnc2_exclusive_bf = (
        positive_unique_count(
            pnc2,
            "exclusivebreastfeeding",
        )
    )

    pnc2_birth_spacing_chosen = (
        positive_unique_count(
            pnc2,
            "birthspacingmethodchosen",
        )
    )

    # ========================================================
    # METHOD DISTRIBUTIONS
    # ========================================================

    pnc1_method_distribution = list(
        pnc1
        .exclude(
            ppfp_method_taken__isnull=True
        )
        .exclude(
            ppfp_method_taken=""
        )
        .values(
            "ppfp_method_taken"
        )
        .annotate(
            total=Count(
                "registerid_id",
                distinct=True,
            )
        )
        .order_by("-total")
    )

    for row in pnc1_method_distribution:
        row["pct"] = percentage(
            row["total"],
            pnc1_ppfp_chosen,
        )

    pnc2_method_distribution = list(
        pnc2
        .exclude(
            birthspacingmethod__isnull=True
        )
        .exclude(
            birthspacingmethod=""
        )
        .values(
            "birthspacingmethod"
        )
        .annotate(
            total=Count(
                "registerid_id",
                distinct=True,
            )
        )
        .order_by("-total")
    )

    for row in pnc2_method_distribution:
        row["pct"] = percentage(
            row["total"],
            pnc2_birth_spacing_chosen,
        )

    # ========================================================
    # RETURN
    # ========================================================

    return {
        "pnc1": {
            "women": pnc1_women,

            "hypertension": (
                pnc1_hypertension
            ),

            "hypertension_pct": percentage(
                pnc1_hypertension,
                pnc1_women,
            ),

            "hypertension_referral_pct": percentage(
                pnc1_hypertension_referral,
                pnc1_hypertension,
            ),

            "average_muac": safe_average(
                pnc1,
                "muac",
            ),

            "anemia": pnc1_anemia,

            "anemia_pct": percentage(
                pnc1_anemia,
                pnc1_women,
            ),

            "mam": pnc1_mam,

            "mam_pct": percentage(
                pnc1_mam,
                pnc1_women,
            ),

            "mam_referral_pct": percentage(
                pnc1_mam_referral,
                pnc1_mam,
            ),

            "sam": pnc1_sam,

            "sam_pct": percentage(
                pnc1_sam,
                pnc1_women,
            ),

            "sam_referral_pct": percentage(
                pnc1_sam_referral,
                pnc1_sam,
            ),

            "maternal_danger_sign": (
                pnc1_maternal_danger_sign
            ),

            "newborn_danger_sign": (
                pnc1_newborn_danger_sign
            ),

            "newborn_death": (
                pnc1_newborn_death
            ),

            "maternal_death": (
                pnc1_maternal_death
            ),

            "newborn_vaccination": (
                pnc1_newborn_vaccination
            ),

            "newborn_vaccination_pct": percentage(
                pnc1_newborn_vaccination,
                pnc1_women,
            ),

            "exclusive_breastfeeding": (
                pnc1_exclusive_bf
            ),

            "exclusive_breastfeeding_pct": percentage(
                pnc1_exclusive_bf,
                pnc1_women,
            ),

            "ppfp_chosen": (
                pnc1_ppfp_chosen
            ),

            "ppfp_chosen_pct": percentage(
                pnc1_ppfp_chosen,
                pnc1_women,
            ),

            "method_distribution": (
                pnc1_method_distribution
            ),
        },

        "pnc2": {
            "women": pnc2_women,

            "hypertension": (
                pnc2_hypertension
            ),

            "hypertension_pct": percentage(
                pnc2_hypertension,
                pnc2_women,
            ),

            "hypertension_referral_pct": percentage(
                pnc2_hypertension_referral,
                pnc2_hypertension,
            ),

            "average_muac": safe_average(
                pnc2,
                "muac",
            ),

            "anemia": pnc2_anemia,

            "anemia_pct": percentage(
                pnc2_anemia,
                pnc2_women,
            ),

            "mam": pnc2_mam,

            "mam_pct": percentage(
                pnc2_mam,
                pnc2_women,
            ),

            "mam_referral_pct": percentage(
                pnc2_mam_referral,
                pnc2_mam,
            ),

            "sam": pnc2_sam,

            "sam_pct": percentage(
                pnc2_sam,
                pnc2_women,
            ),

            "sam_referral_pct": percentage(
                pnc2_sam_referral,
                pnc2_sam,
            ),

            "postnatal_depression": (
                pnc2_depression
            ),

            "postnatal_depression_pct": percentage(
                pnc2_depression,
                pnc2_women,
            ),

            "psychosocial_referral": (
                pnc2_psychosocial_referral
            ),

            "psychosocial_referral_pct": percentage(
                pnc2_psychosocial_referral,
                pnc2_depression,
            ),

            "maternal_danger_sign": (
                pnc2_maternal_danger_sign
            ),

            "newborn_danger_sign": (
                pnc2_newborn_danger_sign
            ),

            "newborn_death": (
                pnc2_newborn_death
            ),

            "maternal_death": (
                pnc2_maternal_death
            ),

            "newborn_vaccination": (
                pnc2_newborn_vaccination
            ),

            "newborn_vaccination_pct": percentage(
                pnc2_newborn_vaccination,
                pnc2_women,
            ),

            "exclusive_breastfeeding": (
                pnc2_exclusive_bf
            ),

            "exclusive_breastfeeding_pct": percentage(
                pnc2_exclusive_bf,
                pnc2_women,
            ),

            "birth_spacing_chosen": (
                pnc2_birth_spacing_chosen
            ),

            "birth_spacing_chosen_pct": percentage(
                pnc2_birth_spacing_chosen,
                pnc2_women,
            ),

            "method_distribution": (
                pnc2_method_distribution
            ),
        },
    }
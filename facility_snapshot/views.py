from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from gancgpnc.models import (
    Gancdelivery,
    Gancenrollment,
    Gancfirstsession,
    Gancfouthsession,
    Gancohort,
    Gancsecondsession,
    Gancthirdsession,
    GroupPncfirstSession,
    GroupPncsecondSession,
)
from hiva.models import (
    Facility,
    HQIPAssessmentHeader,
    Mpdsr,
    Qicdataset,
    aimpee,
    aimpph,
    safesurgeryclinical,
    WhoChildbirthChecklistMonthly,
)
from hmis.models import HMISFact, HMISMonthlySummary
from mentorship.models import Mentorshipdetails, Mentorshipvisit
from skill_lab.models import SkillLab, SkillLabParticipantRecord, SkillLabSession


def _user_province_id(user):
    """Return the user's assigned province, supporting the project's profiles."""
    if user.is_superuser:
        return None

    for relation_name in ("profile", "userprofile"):
        try:
            profile = getattr(user, relation_name, None)
        except Exception:
            profile = None
        if profile is not None:
            province = getattr(profile, "province", None)
            if province is not None:
                return province.pk
    return None


def _check_facility_access(user, facility):
    if user.is_superuser:
        return
    province_id = _user_province_id(user)
    if province_id is None or facility.districtfk.provincefk_id != province_id:
        raise PermissionDenied("You do not have access to this facility.")


@login_required
def facility_list(request):
    """Facility selector, scoped to the logged-in user's province."""
    facilities = Facility.objects.select_related(
        "districtfk__provincefk", "facilitytypefk"
    ).order_by("districtfk__provincefk__name", "districtfk__name", "name")

    if not request.user.is_superuser:
        province_id = _user_province_id(request.user)
        facilities = facilities.filter(districtfk__provincefk_id=province_id) if province_id else facilities.none()

    search = request.GET.get("q", "").strip()
    if search:
        search_filter = Q(name__icontains=search)
        if search.isdigit():
            search_filter |= Q(hfcode=int(search))
        facilities = facilities.filter(search_filter)

    page_obj = Paginator(facilities, 30).get_page(request.GET.get("page"))
    return render(request, "facility_snapshot/facility_list.html", {
        "page_obj": page_obj,
        "search": search,
    })


def _display(value):
    if value is None or value == "":
        return "—"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, Decimal):
        return f"{value:,.0f}" if value == value.to_integral_value() else f"{value:,.2f}"
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)


def _resolve(obj, path):
    value = obj
    for part in path.split("__"):
        if value is None:
            return "—"
        value = getattr(value, part, None)
    return _display(value)


def _table(title, queryset, columns, limit=12, note=""):
    """Build a small, read-only table from a queryset and field paths."""
    objects = list(queryset[:limit])
    return {
        "title": title,
        "columns": [label for label, _path in columns],
        "rows": [[_resolve(obj, path) for _label, path in columns] for obj in objects],
        "empty": not objects,
        "note": note,
        "shown": len(objects),
        "limited": len(objects) == limit,
    }


def _hqip_sections(facility):
    headers = (
        HQIPAssessmentHeader.objects.filter(facilityfk=facility)
        .select_related("assessmenttype", "areafk")
        .prefetch_related("lines__scorefk", "lines__criteriafk")
        .order_by("-assessmentdate", "-id")
    )
    history_rows = []
    latest_gaps = []

    for index, header in enumerate(headers[:20]):
        lines = list(header.lines.all())
        score_names = [
            (line.scorefk.name if line.scorefk_id and line.scorefk else "").strip().casefold()
            for line in lines
        ]
        yes_count = sum(name in {"yes", "met", "fully met"} for name in score_names)
        no_count = sum(name in {"no", "not met", "not available"} for name in score_names)
        na_count = sum(name in {"na", "n/a", "not applicable"} for name in score_names)
        history_rows.append([
            _display(header.assessmentdate),
            _display(header.assessmenttype),
            _display(header.areafk),
            str(len(lines)),
            str(yes_count),
            str(no_count),
            str(na_count),
        ])

        if index == 0:
            for line in lines:
                if not line.scorefk_id or not line.scorefk:
                    continue
                score_name = line.scorefk.name.strip().casefold()
                if score_name in {"no", "not met", "not available"}:
                    criterion = line.criteriafk
                    standard = getattr(criterion, "standardfk", None)
                    section = getattr(standard, "sectionfk", None) if standard else None
                    area = getattr(section, "areafk", None) if section else None
                    latest_gaps.append([
                        _display(area or header.areafk),
                        _display(section),
                        _display(standard),
                        _display(criterion),
                    ])

    return {
        "history": {
            "title": "HQIP assessment history",
            "columns": ["Assessment date", "Round/type", "Thematic area", "Criteria", "Yes", "No", "N/A"],
            "rows": history_rows,
            "empty": not history_rows,
            "note": "Counts are shown from the recorded criteria scores; this table does not apply a separate weighted HQIP formula.",
        },
        "gaps": {
            "title": "Failed criteria in the latest assessment record",
            "columns": ["Thematic area", "Section", "Standard", "Verification criterion"],
            "rows": latest_gaps,
            "empty": not latest_gaps,
            "note": "The latest record is selected by assessment start date. Confirm same-day records when a round has multiple thematic-area headers.",
        },
    }


def _mentorship_table(facility):
    visits = list(
        Mentorshipvisit.objects.filter(facilityfk=facility)
        .order_by("-visitdate", "-id")[:12]
    )
    detail_counts = {
        row["mentorshipvistfk_id"]: row
        for row in (
            Mentorshipdetails.objects.filter(mentorshipvistfk__facilityfk=facility)
            .values("mentorshipvistfk_id")
            .annotate(
                ls_count=Count("id", filter=Q(ls=True)),
                pc_count=Count("id", filter=Q(pc=True)),
                mc_count=Count("id", filter=Q(mc=True)),
                mentee_count=Count("menteename_id", distinct=True),
            )
        )
    }
    rows = []
    for visit in visits:
        counts = detail_counts.get(visit.pk, {})
        rows.append([
            _display(visit.visitdate),
            _display(visit.mentorshipstarttime),
            _display(visit.mentorshipendtime),
            str(counts.get("mentee_count", 0)),
            str(counts.get("ls_count", 0)),
            str(counts.get("pc_count", 0)),
            str(counts.get("mc_count", 0)),
        ])
    return {
        "title": "Clinical mentorship visits",
        "columns": ["Visit date", "Start", "End", "Distinct mentees", "LS", "PC", "MC"],
        "rows": rows,
        "empty": not rows,
        "note": "Counts come from visit detail records. Mentee profile facility is retained separately and may differ from the facility where the visit was recorded.",
    }


def _skill_lab_table(facility):
    sessions = list(
        SkillLabSession.objects.filter(skill_lab__facility=facility)
        .select_related("skill_lab")
        .order_by("-session_date", "-id")[:12]
    )
    participant_counts = {
        row["session_id"]: row
        for row in (
            SkillLabParticipantRecord.objects.filter(session__skill_lab__facility=facility)
            .values("session_id")
            .annotate(
                participants=Count("mentee_name_id", distinct=True),
                ls_count=Count("id", filter=Q(ls=True)),
                mc_count=Count("id", filter=Q(mc=True)),
            )
        )
    }
    rows = []
    for session in sessions:
        counts = participant_counts.get(session.pk, {})
        rows.append([
            _display(session.session_date),
            _display(session.skill_lab),
            _display(session.session_type),
            _display(session.completed_session),
            str(counts.get("participants", 0)),
            str(counts.get("ls_count", 0)),
            str(counts.get("mc_count", 0)),
        ])
    return {
        "title": "MNH Skill Lab sessions",
        "columns": ["Session date", "Skill Lab", "Session type", "Completed", "Distinct participants", "LS", "MC"],
        "rows": rows,
        "empty": not rows,
        "note": "Participant counts are distinct mentees per session. A mentee's assigned facility may differ from the Skill Lab facility.",
    }


def _ganc_summary(facility):
    cohorts = Gancohort.objects.filter(facility=facility)
    enrollments = Gancenrollment.objects.filter(cohortname__facility=facility)
    sessions = {
        "G-ANC session 1": Gancfirstsession.objects.filter(registerid__cohortname__facility=facility).count(),
        "G-ANC session 2": Gancsecondsession.objects.filter(registerid__cohortname__facility=facility).count(),
        "G-ANC session 3": Gancthirdsession.objects.filter(registerid__cohortname__facility=facility).count(),
        "G-ANC session 4": Gancfouthsession.objects.filter(registerid__cohortname__facility=facility).count(),
        "Facility deliveries recorded": Gancdelivery.objects.filter(registerid__cohortname__facility=facility).count(),
        "Group PNC session 1": GroupPncfirstSession.objects.filter(registerid__cohortname__facility=facility).count(),
        "Group PNC session 2": GroupPncsecondSession.objects.filter(registerid__cohortname__facility=facility).count(),
    }
    return {
        "title": "G-ANC / G-PNC activity",
        "columns": ["Measure", "Count"],
        "rows": [["Cohorts", str(cohorts.count())], ["Enrolled women", str(enrollments.count())]]
                + [[label, str(count)] for label, count in sessions.items()],
        "empty": False,
        "note": "Session and delivery records are linked through enrollment to the facility's cohort.",
    }


@login_required
def facility_snapshot(request, facility_id):
    facility = get_object_or_404(
        Facility.objects.select_related("districtfk__provincefk", "facilitytypefk"),
        pk=facility_id,
    )
    _check_facility_access(request.user, facility)

    hqip = _hqip_sections(facility)
    qic = Qicdataset.objects.filter(qicfacility=facility).order_by("-qiccommdate", "-id")
    mpdsr = Mpdsr.objects.filter(facilityname=facility).order_by("-yearmpdsr", "-monthmpdsr", "-id")
    pee = aimpee.objects.filter(aimfacilityname=facility).order_by("-gre_year", "-gre_month", "-id")
    pph = aimpph.objects.filter(aimfacilityname=facility).order_by("-gre_year", "-gre_month", "-id")
    checklist = WhoChildbirthChecklistMonthly.objects.filter(facility_name=facility).order_by("-gre_year", "-gre_month", "-id")
    surgery = safesurgeryclinical.objects.filter(aimfacilityname=facility).order_by("-gre_year", "-gre_month", "-id")

    code_value = facility.hfcode
    code_is_present = code_value not in (None, 0)
    facility_code_match_count = (
        Facility.objects.filter(hfcode=code_value).count() if code_is_present else 0
    )
    hmis_available = code_is_present and facility_code_match_count == 1
    hmis_summaries = HMISMonthlySummary.objects.none()
    hmis_facts = HMISFact.objects.none()
    if hmis_available:
        # Candidate join: HMIS hfid is expected to match HIVA Facility.hfcode.
        # The import source has not been supplied here, so the UI labels this as
        # a code match pending validation against source records.
        hmis_summaries = HMISMonthlySummary.objects.filter(
            hfid=code_value, hiva_hfs=True
        ).order_by("-year", "-month", "-id")
        hmis_facts = HMISFact.objects.filter(
            hfid=code_value, hiva_hfs=True
        ).order_by("-year", "-month", "indicator_name")

    skill_labs = SkillLab.objects.filter(facility=facility)
    skills = _skill_lab_table(facility)
    mentorship = _mentorship_table(facility)
    ganc = _ganc_summary(facility)

    tables = [
        hqip["history"],
        hqip["gaps"],
        _table("QIC and PIP monitoring", qic, [
            ("Meeting date", "qiccommdate"),
            ("QIC score (%)", "qicpercentscore"),
            ("PIP available", "qicpipavail_bool"),
            ("PIP updated", "qicpipupdated_bool"),
            ("Action points", "qicaction_points_count"),
            ("Actions completed", "qicactions_completed_count"),
            ("Follow-up required", "qicfollowup_required"),
        ]),
        _table("MPDSR monthly records", mpdsr, [
            ("Year", "yearmpdsr"), ("Month", "monthmpdsr"),
            ("Maternal deaths reported", "n_maternaldeathreported"),
            ("Maternal deaths reviewed", "n_maternaldeathreviewed"),
            ("Stillbirths reviewed", "nastillbirthreportedreviewed"),
            ("Neonatal deaths reviewed", "nndeath_afteralivebirth_reviewed"),
            ("Recommendations", "recfromMPDSRcommittee"),
        ]),
        _table("AIM-PEE monthly records", pee, [
            ("Period", "period"), ("Baseline/progress", "bl_progress"),
            ("ANC clients", "anc_total_seen"), ("BP measured", "anc_bp_measured"),
            ("Preeclampsia diagnosed", "preeclampsia_diagnosed"),
            ("MgSO₄ within 1 hour", "magnesium_sulfate_within_1hr"),
            ("Maternal deaths", "maternal_death"),
        ]),
        _table("AIM-PPH monthly records", pph, [
            ("Period", "period"), ("Baseline/progress", "bl_progress"),
            ("Total births", "total_births"), ("PPH cases", "pph_total"),
            ("QBL recorded", "qbl_total"), ("Immediate oxytocin", "oxytocin_immediate"),
            ("Transfers out", "transfers_out_pph"),
            ("Maternal deaths", "maternal_death_total_transfer"),
        ]),
        _table("WHO childbirth checklist monthly records", checklist, [
            ("Period", "period"), ("Baseline/progress", "bl_progress"),
            ("Total deliveries", "total_deliveries"), ("Files selected", "files_selected"),
            ("Section 1 complete", "sec1_complete"), ("Section 2 complete", "sec2_complete"),
            ("Section 3 complete", "sec3_complete"), ("Section 4 complete", "sec4_complete"),
            ("All sections complete", "all4_sections_complete"),
        ]),
        _table("Safe Surgery clinical monthly records", surgery, [
            ("Period", "period"), ("Baseline/progress", "bl_progress"),
            ("Cesarean sections", "total_cs"), ("Total deliveries", "total_deliv"),
            ("WHO checklist rate", "who_ssc_rate"), ("Safe tracker rate", "safe_tracker_rate"),
            ("PPH after CS rate", "pph_cs_rate"), ("Post-op fever rate", "postop_fever_rate"),
            ("Maternal deaths", "mat_death_total"),
        ]),
        mentorship,
        skills,
        ganc,
    ]

    hmis_note = (
        f"Candidate match: HMIS hfid = Facility hfcode ({code_value}). Verify this code against the HMIS import source before interpreting the results."
        if hmis_available else
        (f"HF code {code_value} occurs on {facility_code_match_count} Facility records. HMIS is not linked because the code is ambiguous."
         if code_is_present and facility_code_match_count > 1 else
         "No usable Facility HF code is recorded. HMIS rows are not linked until a facility code is available and validated.")
    )
    tables.extend([
        _table("HMIS monthly summary", hmis_summaries, [
            ("Reporting period", "periodcode"), ("ANC1", "anc1"), ("ANC2", "anc2"),
            ("ANC3", "anc3"), ("ANC4", "anc4"), ("PNC1", "pnc1"), ("PNC2", "pnc2"),
            ("Deliveries", "n_delivery"), ("Facility deliveries", "a_delivery"),
            ("Cesarean sections", "c_section"), ("LBW", "lbw"), ("Stillbirths", "stillbirth"),
        ], note=hmis_note),
        _table("HMIS indicator facts", hmis_facts, [
            ("Period", "periodcode"), ("Indicator code", "indicator_code"),
            ("Indicator", "indicator_name"), ("Value", "value"),
        ], limit=30, note=hmis_note),
    ])

    context = {
        "facility": facility,
        "tables": tables,
        "latest_hqip_date": next(iter(HQIPAssessmentHeader.objects.filter(facilityfk=facility).order_by("-assessmentdate").values_list("assessmentdate", flat=True)), None),
        "skill_lab_count": skill_labs.count(),
        "mentorship_visit_count": Mentorshipvisit.objects.filter(facilityfk=facility).count(),
        "hmis_code": code_value,
        "hmis_linked": hmis_available,
        "hmis_duplicate_code": code_is_present and facility_code_match_count > 1,
        "hmis_summary_count": hmis_summaries.count() if hmis_available else 0,
    }
    return render(request, "facility_snapshot/facility_snapshot.html", context)

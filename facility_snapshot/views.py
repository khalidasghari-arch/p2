from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime, time

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Avg, Count, F, Max, Min, Q
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
    HQIPAssessment,
    HQIPAssessmentHeader,
    Mpdsr,
    QICommittee,
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
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, time):
        return value.isoformat(timespec="auto")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    return str(value)


def _resolve(obj, path):
    value = obj
    for part in path.split("__"):
        if value is None:
            return "—"
        value = getattr(value, part, None)
    return _display(value)


def _record_details(obj):
    """Return every saved field, including related identifiers, for a record."""
    details = []
    for field in obj._meta.concrete_fields:
        value = getattr(obj, field.name, None)
        if field.is_relation and field.many_to_one:
            related_id = getattr(obj, field.attname, None)
            rendered = _display(value)
            if related_id is not None:
                rendered = f"{rendered} (ID: {related_id})"
            value = rendered
        details.append({
            "label": str(field.verbose_name or field.name).replace("_", " ").title(),
            "value": _display(value),
        })
    for field in obj._meta.many_to_many:
        related_values = getattr(obj, field.name).all()
        value = ", ".join(str(item) for item in related_values) or "—"
        details.append({
            "label": str(field.verbose_name or field.name).replace("_", " ").title(),
            "value": value,
        })
    return details


def _table(title, queryset, columns, note=""):
    """Build an untruncated table with expandable complete model fields."""
    relation_names = [
        field.name for field in queryset.model._meta.concrete_fields
        if field.is_relation and field.many_to_one and field.name != queryset.model._meta.pk.name
    ]
    if relation_names:
        queryset = queryset.select_related(*relation_names)
    objects = list(queryset)
    return {
        "title": title,
        "columns": [label for label, _path in columns],
        "rows": [{
            "cells": [_resolve(obj, path) for _label, path in columns],
            "details": _record_details(obj),
        } for obj in objects],
        "empty": not objects,
        "note": note,
        "shown": len(objects),
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

    for header in headers:
        lines = list(header.lines.all())
        score_names = [
            (line.scorefk.name if line.scorefk_id and line.scorefk else "").strip().casefold()
            for line in lines
        ]
        yes_count = sum(name in {"yes", "met", "fully met"} for name in score_names)
        no_count = sum(name in {"no", "not met", "not available"} for name in score_names)
        na_count = sum(name in {"na", "n/a", "not applicable"} for name in score_names)
        history_rows.append({
            "cells": [
            _display(header.assessmentdate),
            _display(header.assessmenttype),
            _display(header.areafk),
            str(len(lines)),
            str(yes_count),
            str(no_count),
            str(na_count),
            ],
            "details": _record_details(header),
        })

        for line in lines:
            if not line.scorefk_id or not line.scorefk:
                continue
            score_name = line.scorefk.name.strip().casefold()
            if score_name in {"no", "not met", "not available"}:
                criterion = line.criteriafk
                standard = getattr(criterion, "standardfk", None)
                section = getattr(standard, "sectionfk", None) if standard else None
                area = getattr(section, "areafk", None) if section else None
                latest_gaps.append({
                    "cells": [
                        _display(header.assessmentdate),
                        _display(header.assessmenttype),
                        _display(area or header.areafk),
                        _display(section),
                        _display(standard),
                        _display(criterion),
                        _display(line.scorefk),
                    ],
                    "details": _record_details(line) + _record_details(header),
                })

    return {
        "history": {
            "title": "HQIP assessment history — all rounds",
            "columns": ["Assessment date", "Round/type", "Thematic area", "Criteria", "Yes", "No", "N/A"],
            "rows": history_rows,
            "empty": not history_rows,
            "note": "All assessment headers are included, with no three-round limit. Counts come from recorded criteria scores; this table does not apply a separate weighted HQIP formula.",
        },
        "gaps": {
            "title": "Failed criteria — all assessment rounds",
            "columns": ["Assessment date", "Round/type", "Thematic area", "Section", "Standard", "Verification criterion", "Recorded score"],
            "rows": latest_gaps,
            "empty": not latest_gaps,
            "note": "Every criterion recorded as No/not met is listed with its assessment round and date. This preserves failed criteria from earlier rounds for comparison.",
        },
    }


def _hqip_score_tables(facility):
    """Match HQIPAssessmentDashboard's standard → section → area rollup."""
    YES_ID, NO_ID, NA_ID = 1, 2, 3
    headers = HQIPAssessmentHeader.objects.filter(facilityfk=facility).select_related(
        "assessmenttype"
    )
    round_dates = {}
    for header in headers:
        label = header.assessmenttype.name
        round_dates[label] = min(round_dates.get(label, header.assessmentdate), header.assessmentdate)
    rounds = sorted(round_dates, key=lambda label: (round_dates[label], label.casefold()))
    if not rounds:
        return []

    # Match HQIPContentDashboardAdmin: classify by the criterion's area and
    # ignore records whose criterion hierarchy does not match the header area.
    lines = HQIPAssessment.objects.filter(
        header__facilityfk=facility,
        criteriafk__standardfk__sectionfk__areafk_id=F("header__areafk_id"),
    ).select_related(
        "header__assessmenttype",
        "criteriafk__standardfk__sectionfk__areafk",
        "criteriafk__standardfk__sectionfk",
        "criteriafk__standardfk",
        "criteriafk",
    ).order_by("header__assessmentdate", "header__assessmenttype__name", "id")

    # The admin first computes Yes/(Yes+No) for each standard, then averages
    # scored standards into sections and scored sections into thematic areas.
    standard_counts = {}
    for line in lines:
        header = line.header
        criterion = line.criteriafk
        standard = criterion.standardfk
        section = standard.sectionfk
        area = section.areafk
        area_name = str(area)
        section_name = str(section)
        standard_name = str(standard)
        criterion_name = str(criterion)
        round_name = header.assessmenttype.name
        standard_key = (round_name, area.pk, area_name, section.pk, section_name, standard.pk, standard_name)
        counts = standard_counts.setdefault(standard_key, {"yes": 0, "no": 0, "na": 0, "missing": 0})
        score_id = line.scorefk_id
        if score_id == YES_ID:
            counts["yes"] += 1
        elif score_id == NO_ID:
            counts["no"] += 1
        elif score_id == NA_ID:
            counts["na"] += 1
        else:
            counts["missing"] += 1

    def round2(value):
        return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    def percent(yes, no):
        applicable = yes + no
        return round2(Decimal(yes) / Decimal(applicable) * Decimal("100")) if applicable else None

    def mean(values):
        valid = [Decimal(str(value)) for value in values if value is not None]
        return round2(sum(valid) / Decimal(len(valid))) if valid else None

    def fmt(value):
        return "—" if value is None else f"{value:.2f}%"

    # Compute one percentage for each scored standard, then roll up its parent
    # section and area by the same unweighted means as HQIPAssessmentDashboard.
    std_rows = {}
    for key, counts in standard_counts.items():
        round_name, area_id, area_name, section_id, section_name, standard_id, standard_name = key
        std_rows[(round_name, area_id, area_name, section_id, section_name, standard_id, standard_name)] = {
            **counts,
            "percent": percent(counts["yes"], counts["no"]),
        }

    section_values = {}
    for key, row in std_rows.items():
        round_name, area_id, area_name, section_id, section_name, _std_id, _std_name = key
        section_values.setdefault((round_name, area_id, area_name, section_id, section_name), []).append(row["percent"])
    section_rows = {key: mean(values) for key, values in section_values.items()}

    area_values = {}
    for key, value in section_rows.items():
        round_name, area_id, area_name, _section_id, _section_name = key
        area_values.setdefault((round_name, area_id, area_name), []).append(value)
    area_rows = {key: mean(values) for key, values in area_values.items()}

    def build_matrix(title, dimension, labels, values_by_key):
        dimensions = {}
        for key, value in values_by_key.items():
            round_name = key[0]
            dimension_key = key[1:]
            dimensions.setdefault(dimension_key, {})[round_name] = value
        if not dimensions:
            return {"title": title, "columns": labels + rounds + ["Grand Total"], "rows": [],
                    "empty": True, "note": "No matching scored HQIP records were found."}
        rows = []
        for key, round_scores in sorted(dimensions.items(), key=lambda item: tuple(str(v).casefold() for v in item[0][1::2])):
            scores = [round_scores.get(round_name) for round_name in rounds]
            rows.append({"cells": list(key[1::2]) + [fmt(score) for score in scores] + [fmt(mean(scores))], "details": []})
        if dimension == "area":
            overall_by_round = {
                round_name: mean(
                    value for (row_round, _area_id, _area_name), value in values_by_key.items()
                    if row_round == round_name
                )
                for round_name in rounds
            }
            rows.append({
                "cells": ["Grand Total"]
                         + [fmt(overall_by_round[round_name]) for round_name in rounds]
                         + [fmt(mean(overall_by_round.values()))],
                "details": [],
            })
        return {
            "title": title,
            "columns": labels + rounds + ["Grand Total"],
            "rows": rows,
            "empty": False,
            "note": "Uses the HQIPAssessmentDashboard hierarchy: Standard = Yes ÷ (Yes + No); Section = mean of its scored standards; Thematic Area = mean of its scored sections. N/A and missing responses are excluded from standard denominators. Grand Total is the mean of available round results for that row.",
        }

    tables = [
        build_matrix("HQIP thematic-area comparison — all rounds", "area", ["Thematic area"], area_rows),
        build_matrix("HQIP section scores by round", "section", ["Thematic area", "Section"], section_rows),
        build_matrix("HQIP standard scores by round", "standard", ["Thematic area", "Section", "Standard"],
                     {key: row["percent"] for key, row in std_rows.items()}),
    ]

    # Criterion league table uses the direct Yes/(Yes+No) result per criterion.
    criterion_counts = {}
    for line in lines:
        criterion, standard = line.criteriafk, line.criteriafk.standardfk
        section, area = standard.sectionfk, standard.sectionfk.areafk
        round_name = line.header.assessmenttype.name
        key = (round_name, area.pk, str(area), section.pk, str(section), standard.pk, str(standard), criterion.pk, str(criterion))
        counts = criterion_counts.setdefault(key, [0, 0])
        if line.scorefk_id == YES_ID:
            counts[0] += 1
        elif line.scorefk_id == NO_ID:
            counts[1] += 1
    criterion_scores = {key: percent(counts[0], counts[1]) for key, counts in criterion_counts.items()}
    tables.append(build_matrix(
        "HQIP verification-criteria league table",
        "criterion",
        ["Thematic area", "Section", "Standard", "Verification criterion"],
        criterion_scores,
    ))

    for round_name in rounds:
        scores = {key[1:]: value for key, value in area_rows.items() if key[0] == round_name}
        rows = [{"cells": [area_name, fmt(value)], "details": []}
                for (_area_id, area_name), value in sorted(scores.items(), key=lambda item: item[0][1].casefold())]
        # The periodic dashboard's overall HQIP result is the mean of scored thematic-area results.
        overall = mean(scores.values())
        if rows:
            rows.append({"cells": ["Overall HQIP", fmt(overall)], "details": []})
        tables.append({
            "title": f"HQIP thematic-area results — {round_name}",
            "columns": ["Thematic area", "HQIP %"],
            "rows": rows,
            "empty": not bool(scores),
            "note": f"Round-specific results for {round_name}; uses the admin dashboard's hierarchical area rollup and overall mean of scored thematic areas.",
        })
    return tables


def _mentorship_table(facility):
    visits = list(
        Mentorshipvisit.objects.filter(facilityfk=facility)
        .select_related("facilityfk")
        .order_by("-visitdate", "-id")
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
        rows.append({
            "cells": [
                _display(visit.visitdate),
                _display(visit.mentorshipstarttime),
                _display(visit.mentorshipendtime),
                str(counts.get("mentee_count", 0)),
                str(counts.get("ls_count", 0)),
                str(counts.get("pc_count", 0)),
                str(counts.get("mc_count", 0)),
            ],
            "details": _record_details(visit),
        })
    return {
        "title": "Clinical mentorship visits",
        "columns": ["Visit date", "Start", "End", "Distinct mentees", "LS", "PC", "MC"],
        "rows": rows,
        "empty": not rows,
        "note": "All recorded visits are included. Counts come from visit detail records. Mentee profile facility is retained separately and may differ from the facility where the visit was recorded. Expand a row to see every stored visit field.",
    }


def _skill_lab_table(facility):
    sessions = list(
        SkillLabSession.objects.filter(skill_lab__facility=facility)
        .select_related("skill_lab", "mentor_name", "mentor_org")
        .order_by("-session_date", "-id")
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
        rows.append({
            "cells": [
                _display(session.session_date),
                _display(session.skill_lab),
                _display(session.session_type),
                _display(session.completed_session),
                str(counts.get("participants", 0)),
                str(counts.get("ls_count", 0)),
                str(counts.get("mc_count", 0)),
            ],
            "details": _record_details(session),
        })
    return {
        "title": "MNH Skill Lab sessions",
        "columns": ["Session date", "Skill Lab", "Session type", "Completed", "Distinct participants", "LS", "MC"],
        "rows": rows,
        "empty": not rows,
        "note": "All recorded Skill Lab sessions are included. Participant counts are distinct mentees per session. A mentee's assigned facility may differ from the Skill Lab facility. Expand a row to see every stored session field.",
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
        "rows": [{"cells": ["Cohorts", str(cohorts.count())], "details": []},
                 {"cells": ["Enrolled women", str(enrollments.count())], "details": []}]
                + [{"cells": [label, str(count)], "details": []} for label, count in sessions.items()],
        "empty": False,
        "note": "All cohort, enrollment, session, and delivery records contribute to these counts. Person-level ANC/PNC clinical records are summarized separately in the field-coverage table. Session and delivery records are linked through enrollment to the facility's cohort.",
    }


def _ganc_field_coverage(facility):
    """Summarize every scalar field without exposing patient-level rows."""
    sources = [
        ("G-ANC session 1", Gancfirstsession, {"registerid__cohortname__facility": facility}),
        ("G-ANC session 2", Gancsecondsession, {"registerid__cohortname__facility": facility}),
        ("G-ANC session 3", Gancthirdsession, {"registerid__cohortname__facility": facility}),
        ("G-ANC session 4", Gancfouthsession, {"registerid__cohortname__facility": facility}),
        ("Delivery", Gancdelivery, {"registerid__cohortname__facility": facility}),
        ("Group PNC session 1", GroupPncfirstSession, {"registerid__cohortname__facility": facility}),
        ("Group PNC session 2", GroupPncsecondSession, {"registerid__cohortname__facility": facility}),
    ]
    rows = []
    numeric_types = {
        "IntegerField", "PositiveIntegerField", "SmallIntegerField",
        "PositiveSmallIntegerField", "BigIntegerField", "DecimalField", "FloatField",
    }
    for source_name, model, filters in sources:
        queryset = model.objects.filter(**filters)
        total = queryset.count()
        for field in model._meta.concrete_fields:
            if field.primary_key or field.is_relation:
                continue
            kind = field.get_internal_type()
            field_label = str(field.verbose_name or field.name).replace("_", " ").title()
            if kind == "BooleanField":
                yes = queryset.filter(**{field.name: True}).count()
                no = queryset.filter(**{field.name: False}).count()
                missing = total - yes - no
                summary = f"Yes: {yes}; No: {no}; not recorded: {missing}"
            elif kind in numeric_types:
                stats = queryset.aggregate(
                    recorded=Count(field.name),
                    minimum=Min(field.name),
                    mean=Avg(field.name),
                    maximum=Max(field.name),
                )
                summary = (
                    f"Recorded: {stats['recorded']}/{total}; min: {_display(stats['minimum'])}; "
                    f"mean: {_display(stats['mean'])}; max: {_display(stats['maximum'])}"
                )
            elif kind in {"DateField", "DateTimeField"}:
                dates = queryset.aggregate(first=Min(field.name), last=Max(field.name))
                summary = f"First: {_display(dates['first'])}; last: {_display(dates['last'])}"
            elif field.choices:
                labels = dict(field.flatchoices)
                distribution = queryset.values(field.name).annotate(records=Count("pk")).order_by(field.name)
                summary = "; ".join(
                    f"{labels.get(item[field.name], item[field.name] or 'Not recorded')}: {item['records']}"
                    for item in distribution
                ) or "No records"
            else:
                present = queryset.exclude(**{f"{field.name}__isnull": True})
                if kind in {"CharField", "TextField"}:
                    present = present.exclude(**{field.name: ""})
                summary = f"Entered: {present.count()}/{total}; values remain in the protected source module"
            rows.append({
                "cells": [source_name, field_label, str(total), summary],
                "details": [],
            })
    return {
        "title": "G-ANC/G-PNC clinical indicator field coverage",
        "columns": ["Source model", "Stored field", "Records", "Complete facility-level summary"],
        "rows": rows,
        "empty": not rows,
        "note": "Every non-relational field in the ANC/PNC session and delivery models is represented. Boolean and numeric values are summarized across all records. Person-level names, contact details, free-text remarks, and individual clinical records stay in their source module.",
    }


def _group_dataset_tables(tables):
    """Collect related tables under collapsible dataset headings."""
    datasets = [
        ("hqip", "HQIP assessments", lambda title: title.startswith("HQIP") or title.startswith("Failed criteria")),
        ("qic_pip", "Quality improvement (QIC/PIP)", lambda title: title.startswith("QI committee") or title.startswith("QIC and PIP")),
        ("mpdsr", "MPDSR", lambda title: title.startswith("MPDSR")),
        ("aim", "AIM-PEE and AIM-PPH", lambda title: title.startswith("AIM-PEE") or title.startswith("AIM-PPH")),
        ("childbirth_checklist", "WHO childbirth checklist", lambda title: title.startswith("WHO childbirth checklist")),
        ("safe_surgery", "Safe Surgery", lambda title: title.startswith("Safe Surgery")),
        ("mentorship", "Clinical mentorship", lambda title: title.startswith("Clinical mentorship") or title.startswith("Mentorship learning")),
        ("skill_lab", "MNH Skill Lab", lambda title: title.startswith("MNH Skill Lab")),
        ("ganc_gpnc", "G-ANC / G-PNC", lambda title: title.startswith("G-ANC")),
        ("hmis", "HMIS", lambda title: title.startswith("HMIS")),
    ]
    grouped = []
    for slug, label, matches in datasets:
        matching_tables = [table for table in tables if matches(table["title"])]
        if matching_tables:
            grouped.append({
                "id": f"dataset-{slug}",
                "title": label,
                "tables": matching_tables,
                "table_count": len(matching_tables),
            })
    return grouped


@login_required
def facility_snapshot(request, facility_id):
    facility = get_object_or_404(
        Facility.objects.select_related("districtfk__provincefk", "facilitytypefk"),
        pk=facility_id,
    )
    _check_facility_access(request.user, facility)

    hqip = _hqip_sections(facility)
    hqip_score_tables = _hqip_score_tables(facility)
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
        *hqip_score_tables,
        hqip["history"],
        hqip["gaps"],
        _table("HQIP criterion score records — all rounds", HQIPAssessment.objects.filter(
            header__facilityfk=facility
        ).select_related(
            "header__assessmenttype", "header__areafk", "criteriafk", "scorefk"
        ).order_by(
            "-header__assessmentdate", "header__assessmenttype__name", "header__areafk__name", "criteriafk__id"
        ), [
            ("Assessment date", "header__assessmentdate"),
            ("Round/type", "header__assessmenttype__name"),
            ("Thematic area", "header__areafk__name"),
            ("Verification criterion", "criteriafk__name"),
            ("Score", "scorefk__name"),
        ], note="All criterion-level score records across every assessment round are included. Expand a row to view every stored field."),
        _table("QI committee membership", QICommittee.objects.filter(facility=facility).select_related(
            "facility_staff"
        ).order_by("facility_staff__first_name", "id"), [
            ("Committee member", "facility_staff__first_name"),
            ("Father name", "facility_staff__father_name"),
            ("Role", "role"),
            ("Record status", "record_status"),
        ], note="All membership records are included. Expand a row to view every stored field."),
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
        _ganc_field_coverage(facility),
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
        ], note=hmis_note),
        _table("G-ANC/G-PNC cohort records", Gancohort.objects.filter(facility=facility).order_by("cohortnumber", "id"), [
            ("Cohort", "cohortname"), ("Cohort number", "cohortnumber"),
            ("Status", "cohortstatus"), ("Checklist", "cohortchecklist"),
            ("Target size", "target_size"),
        ], note="All cohort records are included. Expand a row to view every stored cohort field."),
        _table("Mentorship learning and competency records", Mentorshipdetails.objects.filter(
            mentorshipvistfk__facilityfk=facility
        ).select_related(
            "mentorshipvistfk", "menteename", "thematicname", "topicname", "mentor"
        ).order_by(
            "-mentorshipvistfk__visitdate", "mentorshipvistfk_id", "id"
        ), [
            ("Visit date", "mentorshipvistfk__visitdate"),
            ("Mentee", "menteename"),
            ("Thematic area", "thematicname"),
            ("Topic", "topicname"),
            ("Mentor", "mentor"),
            ("LS", "ls"), ("PC", "pc"), ("MC", "mc"),
        ], note="All mentorship detail records for facility visits are included. Expand a row to see every stored detail field."),
        _table("MNH Skill Lab participant records", SkillLabParticipantRecord.objects.filter(
            session__skill_lab__facility=facility
        ).select_related(
            "session__skill_lab", "mentee_name", "thematic_area", "topic"
        ).order_by("-session__session_date", "session_id", "id"), [
            ("Session date", "session__session_date"),
            ("Skill Lab", "session__skill_lab__name"),
            ("Participant", "mentee_name"),
            ("Thematic area", "thematic_area"),
            ("Topic", "topic"),
            ("LS", "ls"), ("MC", "mc"),
            ("Competency status", "competency_status"),
        ], note="All Skill Lab participant records are included. Expand a row to see every stored participant field."),
    ])

    context = {
        "facility": facility,
        "tables": tables,
        "dataset_groups": _group_dataset_tables(tables),
        "latest_hqip_date": next(iter(HQIPAssessmentHeader.objects.filter(facilityfk=facility).order_by("-assessmentdate").values_list("assessmentdate", flat=True)), None),
        "hqip_round_count": HQIPAssessmentHeader.objects.filter(facilityfk=facility).values(
            "assessmentdate", "assessmenttype_id"
        ).distinct().count(),
        "skill_lab_count": skill_labs.count(),
        "mentorship_visit_count": Mentorshipvisit.objects.filter(facilityfk=facility).count(),
        "hmis_code": code_value,
        "hmis_linked": hmis_available,
        "hmis_duplicate_code": code_is_present and facility_code_match_count > 1,
        "hmis_summary_count": hmis_summaries.count() if hmis_available else 0,
    }
    return render(request, "facility_snapshot/facility_snapshot.html", context)

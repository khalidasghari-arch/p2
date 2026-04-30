from django.db.models import Count, Avg, Q
from django.http import JsonResponse

from skill_lab.models import (
    SkillLab,
    SkillLabSession,
    SkillLabParticipantRecord,
    Skill_Lab_Mentee,
)


def dashboard_summary(request):
    total_skill_labs = SkillLab.objects.count()
    total_sessions = SkillLabSession.objects.count()
    total_participant_records = SkillLabParticipantRecord.objects.count()
    total_mentees = Skill_Lab_Mentee.objects.count()

    ls_count = SkillLabParticipantRecord.objects.filter(ls=True).count()
    mc_count = SkillLabParticipantRecord.objects.filter(mc=True).count()

    completed_sessions = SkillLabSession.objects.filter(completed_session=True).count()
    followup_needed = SkillLabSession.objects.filter(followup_needed=True).count()

    avg_checklist_score = SkillLabParticipantRecord.objects.aggregate(
        avg_score=Avg("checklist_score")
    )["avg_score"]

    return JsonResponse({
        "total_skill_labs": total_skill_labs,
        "total_sessions": total_sessions,
        "total_participant_records": total_participant_records,
        "total_mentees": total_mentees,
        "ls_count": ls_count,
        "mc_count": mc_count,
        "completed_sessions": completed_sessions,
        "followup_needed": followup_needed,
        "avg_checklist_score": round(avg_checklist_score or 0, 2),
    })


def sessions_by_province(request):
    data = (
        SkillLabSession.objects
        .values("skill_lab__facility__districtfk__provincefk__name")
        .annotate(total_sessions=Count("id"))
        .order_by("skill_lab__facility__districtfk__provincefk__name")
    )

    results = [
        {
            "province": row["skill_lab__facility__districtfk__provincefk__name"] or "Unknown",
            "total_sessions": row["total_sessions"],
        }
        for row in data
    ]

    return JsonResponse(results, safe=False)


def sessions_by_month(request):
    data = (
        SkillLabSession.objects
        .values("session_date__year", "session_date__month")
        .annotate(total_sessions=Count("id"))
        .order_by("session_date__year", "session_date__month")
    )

    results = [
        {
            "year": row["session_date__year"],
            "month": row["session_date__month"],
            "month_label": f"{row['session_date__year']}-{row['session_date__month']:02d}",
            "total_sessions": row["total_sessions"],
        }
        for row in data
    ]

    return JsonResponse(results, safe=False)


def sessions_by_skill_lab(request):
    data = (
        SkillLabSession.objects
        .values("skill_lab__name")
        .annotate(total_sessions=Count("id"))
        .order_by("-total_sessions")
    )

    results = [
        {
            "skill_lab": row["skill_lab__name"] or "Unknown",
            "total_sessions": row["total_sessions"],
        }
        for row in data
    ]

    return JsonResponse(results, safe=False)


def ls_mc_by_thematic_area(request):
    data = (
        SkillLabParticipantRecord.objects
        .values("thematic_area__name")
        .annotate(
            ls_count=Count("id", filter=Q(ls=True)),
            mc_count=Count("id", filter=Q(mc=True)),
            total_records=Count("id"),
        )
        .order_by("thematic_area__name")
    )

    results = [
        {
            "thematic_area": row["thematic_area__name"] or "Unknown",
            "ls_count": row["ls_count"],
            "mc_count": row["mc_count"],
            "total_records": row["total_records"],
        }
        for row in data
    ]

    return JsonResponse(results, safe=False)


def competency_status(request):
    data = (
        SkillLabParticipantRecord.objects
        .values("competency_status")
        .annotate(total=Count("id"))
        .order_by("competency_status")
    )

    results = [
        {
            "competency_status": row["competency_status"],
            "total": row["total"],
        }
        for row in data
    ]

    return JsonResponse(results, safe=False)


def mentees_by_profession(request):
    data = (
        Skill_Lab_Mentee.objects
        .values("position__name")
        .annotate(total=Count("id"))
        .order_by("-total")
    )

    results = [
        {
            "profession": row["position__name"] or "Unknown",
            "total": row["total"],
        }
        for row in data
    ]

    return JsonResponse(results, safe=False)


def topic_coverage(request):
    data = (
        SkillLabParticipantRecord.objects
        .values("topic__name", "topic__nameeng")
        .annotate(
            total_records=Count("id"),
            ls_count=Count("id", filter=Q(ls=True)),
            mc_count=Count("id", filter=Q(mc=True)),
        )
        .order_by("-total_records")
    )

    results = [
        {
            "topic_code": row["topic__name"] or "Unknown",
            "topic_name": row["topic__nameeng"] or row["topic__name"] or "Unknown",
            "total_records": row["total_records"],
            "ls_count": row["ls_count"],
            "mc_count": row["mc_count"],
        }
        for row in data
    ]

    return JsonResponse(results, safe=False)
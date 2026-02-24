from collections import defaultdict
from django.db.models import Count, Q
from hiva.models import HQIPAssessmentHeader
from hiva.models import HQIPAssessment  # adjust import if HQIPAssessment model is elsewhere
from mentorship.models import MentorshipTopics, MenteeTopicStatus, ThematicMentorship

# --- score IDs in your HQIP setup (confirm: YES=1, NO=2, NA=3) ---
SCORE_YES_ID = 1
SCORE_NO_ID = 2
SCORE_NA_ID = 3
LS_BEFORE_PC = 4  # ✅ your requirement

def _round2(x):
    return round(float(x), 2)

def _pct(yes, applicable):
    if not applicable:
        return None
    return _round2((yes / applicable) * 100.0)

def get_facility_area_priorities(facility_id: int):
    """
    Returns lowest 3 HQIP Area IDs for a facility using hierarchical averaging:
    Standard % = YES / (YES+NO)
    Section %  = average(Standard %)
    Area %     = average(Section %)
    NA excluded (scorefk_id=3 not counted)
    """
    headers_qs = HQIPAssessmentHeader.objects.filter(facilityfk_id=facility_id)
    if not headers_qs.exists():
        return []

    # --- Standard-level rollup (includes Area + Section) ---
    std_rows = (
        HQIPAssessment.objects
        .filter(header__in=headers_qs)
        .values(
            "criteriafk__standardfk__id",
            "criteriafk__standardfk__sectionfk__id",
            "criteriafk__standardfk__sectionfk__areafk__id",
        )
        .annotate(
            yes=Count("id", filter=Q(scorefk_id=SCORE_YES_ID)),
            applicable=Count("id", filter=Q(scorefk_id__in=[SCORE_YES_ID, SCORE_NO_ID])),
        )
    )

    # section_key = (area_id, section_id)
    section_to_std_percents = defaultdict(list)

    for r in std_rows:
        area_id = r["criteriafk__standardfk__sectionfk__areafk__id"]
        section_id = r["criteriafk__standardfk__sectionfk__id"]
        sec_key = (area_id, section_id)

        p = _pct(r["yes"], r["applicable"])
        if p is not None:
            section_to_std_percents[sec_key].append(p)

    # --- Section % = average(Standard %) ---
    area_to_sec_percents = defaultdict(list)
    for (area_id, _section_id), percents in section_to_std_percents.items():
        if not percents:
            continue
        sec_percent = _round2(sum(percents) / len(percents))
        area_to_sec_percents[area_id].append(sec_percent)

    # --- Area % = average(Section %) ---
    area_percents = []
    for area_id, percents in area_to_sec_percents.items():
        if not percents:
            continue
        area_percent = _round2(sum(percents) / len(percents))
        area_percents.append((area_id, area_percent))

    # lowest 3 areas
    area_percents.sort(key=lambda x: x[1])
    return [area_id for area_id, _p in area_percents[:3]]

def get_first_not_competent_topic(mentee_id: int, thematic_id: int):
    """
    Returns first topic (by seq_no then id) in this thematic area that is NOT competent yet.
    """
    topics = (
        MentorshipTopics.objects
        .filter(thematicfk_id=thematic_id)
        .order_by("seq_no", "id")
    )

    competent_topic_ids = set(
        MenteeTopicStatus.objects.filter(
            mentee_id=mentee_id,
            topic__thematicfk_id=thematic_id,
            status="COMPETENT",
        ).values_list("topic_id", flat=True)
    )

    for t in topics:
        if t.id not in competent_topic_ids:
            return t
    return None

def recommend_next_for_staff_in_facility(staff_id: int, facility_id: int):
    """
    Professional rules:
    - HQIP chooses lowest 3 HQIP Area IDs
    - Those map to mentorship thematic areas via ThematicMentorship.hqip_area_id
    - Topic selection uses thematicfk + seq_no order
    - NOT competent:
        - if consecutive_ls < 4 -> LS
        - else -> PC (support_flag True)
    - COMPETENT -> next topic by seq_no
    """
    priority_area_ids = get_facility_area_priorities(facility_id)
    if not priority_area_ids:
        return {
            "topic": None, "track": None, "session_type": None,
            "support_flag": False,
            "reason": "No HQIP assessments found for this facility.",
        }

    # map HQIP areas -> mentorship thematics (must be configured in admin)
    thematics = list(
        ThematicMentorship.objects.filter(hqip_area_id__in=priority_area_ids).select_related("hqip_area")
    )

    if not thematics:
        return {
            "topic": None, "track": None, "session_type": None,
            "support_flag": False,
            "reason": "No mentorship thematic areas mapped to HQIP areas. Please map ThematicMentorship.hqip_area.",
        }

    # keep thematics in the SAME priority order of HQIP (lowest first)
    thematic_by_area = {t.hqip_area_id: t for t in thematics}
    ordered_thematics = [thematic_by_area[a] for a in priority_area_ids if a in thematic_by_area]

    selected_topic = None
    selected_thematic = None

    for th in ordered_thematics:
        topic = get_first_not_competent_topic(staff_id, th.id)
        if topic:
            selected_topic = topic
            selected_thematic = th
            break

    if not selected_topic:
        return {
            "topic": None, "track": None, "session_type": None,
            "support_flag": False,
            "reason": "Mentee competent in all topics under the facility’s priority thematic areas.",
        }

    st = MenteeTopicStatus.objects.filter(
        mentee_id=staff_id,
        topic_id=selected_topic.id
    ).first()

    # no history -> start LS
    if not st:
        return {
            "topic": selected_topic,
            "track": selected_thematic.name,
            "session_type": "LS",
            "support_flag": False,
            "reason": f"Priority area: {selected_thematic.name}. Start LS (1/{LS_BEFORE_PC}).",
        }

    # not competent -> LS until threshold, then PC
    if st.status != "COMPETENT":
        if st.consecutive_ls < LS_BEFORE_PC:
            return {
                "topic": selected_topic,
                "track": selected_thematic.name,
                "session_type": "LS",
                "support_flag": False,
                "reason": f"Continue LS ({st.consecutive_ls}/{LS_BEFORE_PC}) before PC.",
            }
        return {
            "topic": selected_topic,
            "track": selected_thematic.name,
            "session_type": "PC",
            "support_flag": True,
            "reason": f"{LS_BEFORE_PC} consecutive LS completed → recommend PC assessment.",
        }

    # competent -> next topic in same thematic area (SNC-1 -> SNC-2)
    next_topic = (
        MentorshipTopics.objects
        .filter(thematicfk_id=selected_topic.thematicfk_id, seq_no__gt=selected_topic.seq_no)
        .order_by("seq_no", "id")
        .first()
    )

    if not next_topic:
        return {
            "topic": None,
            "track": selected_thematic.name,
            "session_type": None,
            "support_flag": False,
            "reason": f"All topics completed in {selected_thematic.name}.",
        }

    return {
        "topic": next_topic,
        "track": selected_thematic.name,
        "session_type": "LS",
        "support_flag": False,
        "reason": f"Competent → advance to next topic {next_topic.name}.",
    }
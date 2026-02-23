from django.db.models import Q
from hiva.models import HQIPAssessmentHeader
from mentorship.models import MentorshipTopics, MenteeTopicStatus
from hiva.models import HQIPAssessmentHeader
from hiva.admin import AssessmentHeaderAdmin
from django.contrib.admin.sites import site

def get_facility_area_priorities(facility_id: int):
    """
    Returns lowest 3 HQIP areas using EXACT SAME logic
    as admin dashboards (hierarchical averaging).
    """

    headers = HQIPAssessmentHeader.objects.filter(
        facilityfk_id=facility_id
    )

    if not headers.exists():
        return []

    # Create admin instance to access shared method
    admin_instance = AssessmentHeaderAdmin(
        HQIPAssessmentHeader,
        site
    )

    _std, _sec, area_results = admin_instance._compute_hqip_rollups(headers)

    # Remove None
    scored = [x for x in area_results if x["percent"] is not None]

    # Sort lowest first
    scored_sorted = sorted(scored, key=lambda x: x["percent"])

    # Return top 3 lowest FULL area names (must match MentorshipTopics.track)
    return [x["area"].strip() for x in scored_sorted[:3]]

# ============================================================
# 2️⃣ FIRST NON-COMPETENT TOPIC IN TRACK
# ============================================================

def get_first_not_competent_topic(mentee_id: int, track: str):

    # Get unique seq_no values only
    seq_numbers = (
        MentorshipTopics.objects
        .filter(track=track)
        .values_list("seq_no", flat=True)
        .distinct()
        .order_by("seq_no")
    )

    for seq in seq_numbers:

        # Pick canonical topic (lowest id) for this seq_no
        topic = (
            MentorshipTopics.objects
            .filter(track=track, seq_no=seq)
            .order_by("id")
            .first()
        )

        if not topic:
            continue

        is_competent = MenteeTopicStatus.objects.filter(
            mentee_id=mentee_id,
            topic__track=track,
            topic__seq_no=seq,
            status="COMPETENT",
        ).exists()

        if not is_competent:
            return topic

    return None

# ============================================================
# 3️⃣ MAIN RECOMMENDATION ENGINE
# ============================================================

def recommend_next_for_staff_in_facility(staff_id: int, facility_id: int):
    """
    Uses HQIP lowest 3 thematic areas.
    Applies professional LS → PC → progression logic.

    Rules:
    - Minimum 3 LS required before PC
    - After COMPETENT → move to next topic by seq_no
    """

    tracks = get_facility_area_priorities(facility_id)

    if not tracks:
        return {
            "topic": None,
            "track": None,
            "session_type": None,
            "support_flag": False,
            "reason": "No HQIP data available for this facility.",
        }

    selected_topic = None
    selected_track = None

    # 1️⃣ Find first not-competent topic from priority tracks
    for tr in tracks:
        topic = get_first_not_competent_topic(staff_id, tr)
        if topic:
            selected_topic = topic
            selected_track = tr
            break

    if not selected_topic:
        return {
            "topic": None,
            "track": None,
            "session_type": None,
            "support_flag": False,
            "reason": "Mentee competent in all priority tracks.",
        }

    # 2️⃣ Get status object
    status_obj = MenteeTopicStatus.objects.filter(
        mentee_id=staff_id,
        topic=selected_topic
    ).first()

    # 3️⃣ No previous status → start LS
    if not status_obj:
        return {
            "topic": selected_topic,
            "track": selected_track,
            "session_type": "LS",
            "support_flag": False,
            "reason": f"HQIP gap in {selected_track}. Start LS (1/3).",
        }

    # 4️⃣ NOT competent yet
    if status_obj.status != "COMPETENT":

        # Require minimum 3 LS before PC
        if status_obj.consecutive_ls < 3:
            return {
                "topic": selected_topic,
                "track": selected_track,
                "session_type": "LS",
                "support_flag": False,
                "reason": f"Continue LS ({status_obj.consecutive_ls}/3 required before PC).",
            }

        # After 3 LS → escalate to PC
        return {
            "topic": selected_topic,
            "track": selected_track,
            "session_type": "PC",
            "support_flag": True,
            "reason": "3 consecutive LS completed → competency assessment required (PC).",
        }

    # 5️⃣ If COMPETENT → move to next topic in same track
    next_topic = (
        MentorshipTopics.objects
        .filter(
            track=selected_topic.track,
            seq_no__gt=selected_topic.seq_no
        )
        .order_by("seq_no")
        .first()
    )

    if not next_topic:
        return {
            "topic": None,
            "track": selected_track,
            "session_type": None,
            "support_flag": False,
            "reason": f"All topics completed in {selected_track}.",
        }

    return {
        "topic": next_topic,
        "track": selected_track,
        "session_type": "LS",
        "support_flag": False,
        "reason": f"Advance to next topic {next_topic.shortname}.",
    }
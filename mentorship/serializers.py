from rest_framework import serializers
from .models import Mentorshipdetails


class MentorshipDataSerializer(serializers.ModelSerializer):

    Province = serializers.CharField(
        source="visit_id.facility_name.districtfk.provincefk.name"
    )

    District = serializers.CharField(
        source="visit_id.facility_name.districtfk.name"
    )

    HF_Name = serializers.CharField(
        source="visit_id.facility_name.name"
    )

    FacilityType = serializers.CharField(
        source="visit_id.facility_name.facilitytype"
    )

    Mentor = serializers.CharField(
        source="visit_id.mentor.full_name"
    )

    Topic = serializers.CharField(
        source="topicfk.name"
    )

    Thematic = serializers.CharField(
        source="topicfk.thematicfk.name"
    )

    MenteeName = serializers.CharField(
        source="mentee.full_name"
    )

    class Meta:
        model = Mentorshipdetails

        fields = [
            "id",
            "visit_id",
            "Province",
            "District",
            "HF_Name",
            "FacilityType",
            "Mentor",
            "LS",
            "PC",
            "MC",
            "Topic",
            "Thematic",
            "mentee",
            "MenteeName",
            "created_at",
        ]
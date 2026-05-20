from rest_framework.views import APIView
from rest_framework.response import Response

from django.core.cache import cache
from django.db.models import Count, CharField, Value
from django.db.models.functions import (
    TruncMonth,
    TruncDate,
    Cast,
    Lower,
    Trim,
    Concat,
)

from mentorship.models import Mentorshipvisit, Mentorshipdetails
from hiva.models import Province, District, Facility


# ============================================================
# Shared business rule:
# One mentorship visit = unique Visit Date + Mentor
# Same Visit Date + same Mentor = counted once only
# Same Visit Date + different Mentor = counted separately
# ============================================================

def mentor_visit_key_expr():
    """
    Creates the unique key used for counting mentorship visits.

    Business rule:
    Visit Date + Mentor = 1 mentorship visit
    """
    return Concat(
        Cast(
            TruncDate("mentorshipvistfk__visitdate"),
            output_field=CharField(),
        ),
        Value("|"),
        Lower(Trim("mentor__name")),
        output_field=CharField(),
    )


def get_filtered_mentorship_details(request):
    """
    Returns Mentorshipdetails filtered by dashboard filters.

    Important:
    We use Mentorshipdetails, not Mentorshipvisit, because mentor is available
    at detail level.
    """

    province_id = request.GET.get("province")
    district_id = request.GET.get("district")
    facility_id = request.GET.get("facility")
    year = request.GET.get("year")

    qs = Mentorshipdetails.objects.filter(
        mentorshipvistfk__visitdate__isnull=False,
        mentor__name__isnull=False,
    ).exclude(
        mentor__name=""
    )

    if province_id:
        qs = qs.filter(
            mentorshipvistfk__facilityfk__districtfk__provincefk_id=province_id
        )

    if district_id:
        qs = qs.filter(
            mentorshipvistfk__facilityfk__districtfk_id=district_id
        )

    if facility_id:
        qs = qs.filter(
            mentorshipvistfk__facilityfk_id=facility_id
        )

    if year:
        qs = qs.filter(
            mentorshipvistfk__visitdate__year=year
        )

    return qs


class DashboardFilterOptionsAPI(APIView):
    def get(self, request):
        province_id = request.GET.get("province")
        district_id = request.GET.get("district")

        provinces = list(
            Province.objects.order_by("name").values("id", "name")
        )

        districts_qs = District.objects.all()
        if province_id:
            districts_qs = districts_qs.filter(provincefk_id=province_id)

        districts = list(
            districts_qs.order_by("name").values("id", "name", "provincefk_id")
        )

        facilities_qs = Facility.objects.all()
        if district_id:
            facilities_qs = facilities_qs.filter(districtfk_id=district_id)
        elif province_id:
            facilities_qs = facilities_qs.filter(districtfk__provincefk_id=province_id)

        facilities = list(
            facilities_qs.order_by("name").values("id", "name", "districtfk_id")
        )

        years_qs = (
            Mentorshipvisit.objects.exclude(visitdate__isnull=True)
            .dates("visitdate", "year", order="DESC")
        )
        years = [d.year for d in years_qs]

        return Response({
            "provinces": provinces,
            "districts": districts,
            "facilities": facilities,
            "years": years,
        })


class DashboardSummaryAPI(APIView):
    def get(self, request):
        province_id = request.GET.get("province")
        district_id = request.GET.get("district")
        facility_id = request.GET.get("facility")

        facilities = Facility.objects.all()

        if province_id:
            facilities = facilities.filter(
                districtfk__provincefk_id=province_id
            )

        if district_id:
            facilities = facilities.filter(
                districtfk_id=district_id
            )

        if facility_id:
            facilities = facilities.filter(
                id=facility_id
            )

        details_qs = get_filtered_mentorship_details(request)

        total_facilities = facilities.count()

        total_visits = details_qs.aggregate(
            total=Count(mentor_visit_key_expr(), distinct=True)
        )["total"] or 0

        reporting_facilities = (
            details_qs
            .values("mentorshipvistfk__facilityfk_id")
            .distinct()
            .count()
        )

        reporting_rate = (
            round((reporting_facilities / total_facilities) * 100, 1)
            if total_facilities else 0
        )

        return Response({
            "total_visits": total_visits,
            "reporting_facilities": reporting_facilities,
            "total_facilities": total_facilities,
            "reporting_rate": reporting_rate,
        })


class DashboardTrendsAPI(APIView):
    def get(self, request):
        details_qs = get_filtered_mentorship_details(request)

        qs = (
            details_qs
            .annotate(month=TruncMonth("mentorshipvistfk__visitdate"))
            .values("month")
            .annotate(value=Count(mentor_visit_key_expr(), distinct=True))
            .order_by("month")
        )

        data = [
            {
                "month": item["month"].strftime("%b"),
                "value": item["value"],
            }
            for item in qs
            if item["month"]
        ]

        return Response(data)


class DashboardByProvinceAPI(APIView):
    def get(self, request):
        details_qs = get_filtered_mentorship_details(request)

        qs = (
            details_qs
            .values("mentorshipvistfk__facilityfk__districtfk__provincefk__name")
            .annotate(value=Count(mentor_visit_key_expr(), distinct=True))
            .order_by("-value")
        )

        data = [
            {
                "province": item["mentorshipvistfk__facilityfk__districtfk__provincefk__name"],
                "value": item["value"],
            }
            for item in qs
            if item["mentorshipvistfk__facilityfk__districtfk__provincefk__name"]
        ]

        return Response(data)


class TopFacilitiesAPI(APIView):
    def get(self, request):
        province_id = request.GET.get("province")
        district_id = request.GET.get("district")
        facility_id = request.GET.get("facility")
        year = request.GET.get("year")

        cache_key = f"top_facilities:{province_id}:{district_id}:{facility_id}:{year}"
        cached_data = cache.get(cache_key)

        if cached_data:
            return Response(cached_data)

        details_qs = get_filtered_mentorship_details(request)

        qs = (
            details_qs
            .values("mentorshipvistfk__facilityfk__name")
            .annotate(visits=Count(mentor_visit_key_expr(), distinct=True))
            .order_by("-visits")[:10]
        )

        result = [
            {
                "facility": item["mentorshipvistfk__facilityfk__name"],
                "visits": item["visits"],
            }
            for item in qs
            if item["mentorshipvistfk__facilityfk__name"]
        ]

        cache.set(cache_key, result, 300)

        return Response(result)
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count
from django.db.models.functions import TruncMonth
from mentorship.models import Mentorshipvisit
from hiva.models import Province, District, Facility

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
        year = request.GET.get("year")

        facilities = Facility.objects.all()
        visits = Mentorshipvisit.objects.all()

        if province_id:
            facilities = facilities.filter(districtfk__provincefk_id=province_id)
            visits = visits.filter(facilityfk__districtfk__provincefk_id=province_id)

        if district_id:
            facilities = facilities.filter(districtfk_id=district_id)
            visits = visits.filter(facilityfk__districtfk_id=district_id)

        if facility_id:
            facilities = facilities.filter(id=facility_id)
            visits = visits.filter(facilityfk_id=facility_id)

        if year:
            visits = visits.filter(visitdate__year=year)

        total_facilities = facilities.count()
        total_visits = visits.count()
        reporting_facilities = visits.values("facilityfk").distinct().count()

        reporting_rate = round((reporting_facilities / total_facilities) * 100, 1) if total_facilities else 0

        return Response({
            "total_visits": total_visits,
            "reporting_facilities": reporting_facilities,
            "total_facilities": total_facilities,
            "reporting_rate": reporting_rate,
        })


class DashboardTrendsAPI(APIView):
    def get(self, request):
        province_id = request.GET.get("province")
        district_id = request.GET.get("district")
        facility_id = request.GET.get("facility")
        year = request.GET.get("year")

        qs = Mentorshipvisit.objects.all()

        if province_id:
            qs = qs.filter(facilityfk__districtfk__provincefk_id=province_id)

        if district_id:
            qs = qs.filter(facilityfk__districtfk_id=district_id)

        if facility_id:
            qs = qs.filter(facilityfk_id=facility_id)

        if year:
            qs = qs.filter(visitdate__year=year)

        qs = (
            qs.annotate(month=TruncMonth("visitdate"))
            .values("month")
            .annotate(value=Count("id"))
            .order_by("month")
        )

        data = [
            {
                "month": item["month"].strftime("%b"),
                "value": item["value"],
            }
            for item in qs if item["month"]
        ]

        return Response(data)

class DashboardByProvinceAPI(APIView):
    def get(self, request):
        district_id = request.GET.get("district")
        facility_id = request.GET.get("facility")
        year = request.GET.get("year")

        qs = Mentorshipvisit.objects.all()

        if district_id:
            qs = qs.filter(facilityfk__districtfk_id=district_id)

        if facility_id:
            qs = qs.filter(facilityfk_id=facility_id)

        if year:
            qs = qs.filter(visitdate__year=year)

        qs = (
            qs.values("facilityfk__districtfk__provincefk__name")
            .annotate(value=Count("id"))
            .order_by("-value")
        )

        data = [
            {
                "province": item["facilityfk__districtfk__provincefk__name"],
                "value": item["value"],
            }
            for item in qs if item["facilityfk__districtfk__provincefk__name"]
        ]

        return Response(data)
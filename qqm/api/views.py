from rest_framework.views import APIView
from rest_framework.response import Response

from qqm.services.analysis import get_facility_analysis, get_facility_trend


class QQMFacilityAnalysisAPI(APIView):
    def get(self, request):
        hfcodes = request.GET.getlist("hfcode")
        round_name = request.GET.get("round")

        cleaned_hfcodes = []

        for code in hfcodes:
            try:
                cleaned_hfcodes.append(int(str(code).lstrip("0")))
            except Exception:
                pass

        data = list(
            get_facility_analysis(
                hfcodes=cleaned_hfcodes if cleaned_hfcodes else None,
                round_name=round_name,
            )
        )

        return Response(data)


class QQMFacilityTrendAPI(APIView):
    def get(self, request, hfcode):
        try:
            clean_code = int(str(hfcode).lstrip("0"))
        except Exception:
            return Response({"error": "Invalid HFCode"}, status=400)

        data = list(get_facility_trend(clean_code))
        return Response(data)
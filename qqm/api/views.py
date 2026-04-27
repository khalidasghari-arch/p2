from rest_framework.views import APIView
from rest_framework.response import Response
from qqm.services.analysis import get_facility_analysis, get_facility_trend
from qqm.models import QQMStructuralDetail


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

class QQMStructuralDomainAPI(APIView):
    def get(self, request, hfcode):
        round_name = request.GET.get("round")

        qs = QQMStructuralDetail.objects.select_related(
            "score",
            "score__upload",
            "score__facility",
        ).filter(
            score__hfcode=hfcode,
        )

        if round_name:
            qs = qs.filter(score__upload__round_name=round_name)

        obj = qs.order_by("-score__upload__uploaded_at").first()

        if not obj:
            return Response({"error": "No structural domain data found"}, status=404)

        data = {
            "hfcode": obj.score.hfcode,
            "hfname": obj.score.facility.name if obj.score.facility else obj.score.hfname_excel,
            "round": obj.score.upload.round_name,
            "domains": [
                {
                    "domain": "Domain 1: General Management",
                    "short_name": "General Management",
                    "score": obj.d1_general_management,
                    "percent": round(obj.d1_general_management * 100, 2) if obj.d1_general_management is not None else None,
                },
                {
                    "domain": "Domain 2: Hygiene",
                    "short_name": "Hygiene",
                    "score": obj.d2_hygiene,
                    "percent": round(obj.d2_hygiene * 100, 2) if obj.d2_hygiene is not None else None,
                },
                {
                    "domain": "Domain 3: OPD / Curative Consultations",
                    "short_name": "OPD / Curative Consultations",
                    "score": obj.d3_opd,
                    "percent": round(obj.d3_opd * 100, 2) if obj.d3_opd is not None else None,
                },
                {
                    "domain": "Domain 4: Family Planning",
                    "short_name": "Family Planning",
                    "score": obj.d4_fp,
                    "percent": round(obj.d4_fp * 100, 2) if obj.d4_fp is not None else None,
                },
                {
                    "domain": "Domain 5: Laboratory",
                    "short_name": "Laboratory",
                    "score": obj.d5_lab,
                    "percent": round(obj.d5_lab * 100, 2) if obj.d5_lab is not None else None,
                },
                {
                    "domain": "Domain 6: Essential Drugs Management",
                    "short_name": "Essential Drugs Management",
                    "score": obj.d6_drugs,
                    "percent": round(obj.d6_drugs * 100, 2) if obj.d6_drugs is not None else None,
                },
                {
                    "domain": "Domain 7: Tracer Drugs",
                    "short_name": "Tracer Drugs",
                    "score": obj.d7_tracer,
                    "percent": round(obj.d7_tracer * 100, 2) if obj.d7_tracer is not None else None,
                },
                {
                    "domain": "Domain 8: Maternity",
                    "short_name": "Maternity",
                    "score": obj.d8_maternity,
                    "percent": round(obj.d8_maternity * 100, 2) if obj.d8_maternity is not None else None,
                },
                {
                    "domain": "Domain 9: EPI",
                    "short_name": "EPI",
                    "score": obj.d9_epi,
                    "percent": round(obj.d9_epi * 100, 2) if obj.d9_epi is not None else None,
                },
                {
                    "domain": "Domain 10: Antenatal Care",
                    "short_name": "Antenatal Care",
                    "score": obj.d10_anc,
                    "percent": round(obj.d10_anc * 100, 2) if obj.d10_anc is not None else None,
                },
            ],
        }

        return Response(data)

class QQMStructuralDomainMultiFacilityAPI(APIView):
    def get(self, request):
        round_name = request.GET.get("round")
        hfcodes = request.GET.getlist("hfcode")

        cleaned_hfcodes = []
        for code in hfcodes:
            try:
                cleaned_hfcodes.append(int(str(code).lstrip("0")))
            except Exception:
                pass

        qs = QQMStructuralDetail.objects.select_related(
            "score",
            "score__upload",
            "score__facility",
        )

        if cleaned_hfcodes:
            qs = qs.filter(score__hfcode__in=cleaned_hfcodes)

        if round_name:
            qs = qs.filter(score__upload__round_name=round_name)

        results = []

        for obj in qs.order_by("score__hfcode"):
            results.append({
                "hfcode": obj.score.hfcode,
                "hfname": obj.score.facility.name if obj.score.facility else obj.score.hfname_excel,
                "round": obj.score.upload.round_name,
                "general_management": round(obj.d1_general_management * 100, 2) if obj.d1_general_management is not None else None,
                "hygiene": round(obj.d2_hygiene * 100, 2) if obj.d2_hygiene is not None else None,
                "opd": round(obj.d3_opd * 100, 2) if obj.d3_opd is not None else None,
                "family_planning": round(obj.d4_fp * 100, 2) if obj.d4_fp is not None else None,
                "laboratory": round(obj.d5_lab * 100, 2) if obj.d5_lab is not None else None,
                "essential_drugs": round(obj.d6_drugs * 100, 2) if obj.d6_drugs is not None else None,
                "tracer_drugs": round(obj.d7_tracer * 100, 2) if obj.d7_tracer is not None else None,
                "maternity": round(obj.d8_maternity * 100, 2) if obj.d8_maternity is not None else None,
                "epi": round(obj.d9_epi * 100, 2) if obj.d9_epi is not None else None,
                "anc": round(obj.d10_anc * 100, 2) if obj.d10_anc is not None else None,
            })

        return Response(results)
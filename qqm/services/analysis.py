def get_facility_analysis(hfcodes=None, round_name=None):
    from qqm.models import QQMFacilityScore

    qs = QQMFacilityScore.objects.select_related(
        "upload",
        "facility",
    ).all()

    if hfcodes:
        qs = qs.filter(hfcode__in=hfcodes)

    if round_name:
        qs = qs.filter(upload__round_name=round_name)

    return qs.values(
        "hfcode",
        "hfname_excel",
        "facility__name",
        "facility__districtfk__name",
        "facility__districtfk__provincefk__name",
        "upload__round_name",
        "structural_score",
        "outcome_score",
        "content_score",
        "qqm_score",
    )


def get_facility_trend(hfcode):
    from qqm.models import QQMFacilityScore

    return QQMFacilityScore.objects.filter(
        hfcode=hfcode
    ).select_related("upload").order_by(
        "upload__round_name"
    ).values(
        "hfcode",
        "hfname_excel",
        "upload__round_name",
        "structural_score",
        "outcome_score",
        "content_score",
        "qqm_score",
    )
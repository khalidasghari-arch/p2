from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render
from django.utils.timezone import now
from .models import KMDocument, KMRecommendation, THEME_CHOICES
from .utils import user_province
from django.http import JsonResponse
from hiva.models import District, Facility

def _int_or_none(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None

@login_required
def km_dashboard(request):
    # -----------------------
    # Read filters
    # -----------------------
    year = _int_or_none(request.GET.get("year"))
    month = _int_or_none(request.GET.get("month"))
    theme = request.GET.get("theme") or ""
    facility_id = _int_or_none(request.GET.get("facility"))
    district_id = _int_or_none(request.GET.get("district"))
    province_id = _int_or_none(request.GET.get("province"))

    today = now()
    if not year:
        year = today.year

    # -----------------------
    # Base querysets
    # -----------------------
    docs = KMDocument.objects.all()
    recs = KMRecommendation.objects.all()

    # Province restriction
    up = user_province(request)
    if up:
        docs = docs.filter(province=up)
        recs = recs.filter(province=up)
    else:
        # if not restricted, allow province filter
        if province_id:
            docs = docs.filter(province_id=province_id)
            recs = recs.filter(province_id=province_id)

    # Apply filters
    docs = docs.filter(year=year)
    recs = recs.filter(year=year)

    if month:
        docs = docs.filter(month=month)
        recs = recs.filter(month=month)

    if theme:
        docs = docs.filter(theme=theme)
        recs = recs.filter(theme=theme)

    if district_id:
        docs = docs.filter(district_id=district_id)
        recs = recs.filter(district_id=district_id)

    if facility_id:
        docs = docs.filter(facility_id=facility_id)
        recs = recs.filter(facility_id=facility_id)

    # -----------------------
    # KPIs
    # -----------------------
    total_docs = docs.count()
    total_recs = recs.count()
    implemented = recs.filter(status="done").count()
    pending = recs.filter(status__in=["pending", "in_progress", "blocked"]).count()

    impl_rate = (implemented / total_recs * 100) if total_recs else 0

    # -----------------------
    # Trend (monthly counts)
    # -----------------------
    # docs by month
    docs_trend = (
        KMDocument.objects
        .filter(year=year)
        .filter(province=up) if up else KMDocument.objects.filter(year=year)
    )
    if not up and province_id:
        docs_trend = docs_trend.filter(province_id=province_id)
    if theme:
        docs_trend = docs_trend.filter(theme=theme)

    docs_trend = (
        docs_trend.values("month")
        .annotate(n=Count("id"))
        .order_by("month")
    )

    # recs implemented by month
    recs_trend = (
        KMRecommendation.objects
        .filter(year=year)
        .filter(province=up) if up else KMRecommendation.objects.filter(year=year)
    )
    if not up and province_id:
        recs_trend = recs_trend.filter(province_id=province_id)
    if theme:
        recs_trend = recs_trend.filter(theme=theme)

    recs_impl_trend = (
        recs_trend.values("month")
        .annotate(
            total=Count("id"),
            done=Count("id", filter=Q(status="done")),
        )
        .order_by("month")
    )

    # -----------------------
    # Facility table snapshot
    # -----------------------
    facility_stats = (
        recs.values("facility__id", "facility__name")
        .annotate(
            total=Count("id"),
            done=Count("id", filter=Q(status="done")),
            pending=Count("id", filter=Q(status__in=["pending", "in_progress", "blocked"])),
        )
        .order_by("-pending", "facility__name")
    )
    # compute rate in python (safe & simple)
    facility_table = []
    for r in facility_stats:
        total = r["total"] or 0
        done = r["done"] or 0
        rate = (done / total * 100) if total else 0
        facility_table.append({
            "facility_id": r["facility__id"],
            "facility_name": r["facility__name"],
            "total": total,
            "done": done,
            "pending": r["pending"] or 0,
            "rate": round(rate, 1),
        })

    context = {
        "filters": {
            "year": year, "month": month, "theme": theme,
            "province_id": province_id, "district_id": district_id, "facility_id": facility_id,
        },
        "kpis": {
            "total_docs": total_docs,
            "total_recs": total_recs,
            "implemented": implemented,
            "pending": pending,
            "impl_rate": round(impl_rate, 1),
        },
        "docs_trend": list(docs_trend),
        "recs_impl_trend": list(recs_impl_trend),
        "facility_table": facility_table,
        "themes": THEME_CHOICES,
        "is_restricted": bool(up),
        "restricted_province": up,
    }
    return render(request, "km_dashboard/dashboard.html", context)
@login_required
def districts_api(request):
    province_id = request.GET.get("province_id")
    qs = District.objects.all()

    up = user_province(request)
    if up:
        qs = qs.filter(provincefk=up)  # adjust field name if different
    elif province_id:
        qs = qs.filter(provincefk_id=province_id)  # adjust if different

    data = list(qs.values("id", "name").order_by("name"))
    return JsonResponse({"results": data})

@login_required
def facilities_api(request):
    district_id = request.GET.get("district_id")
    qs = Facility.objects.all()

    up = user_province(request)
    if up:
        qs = qs.filter(districtfk__provincefk=up)  # adjust if different
    if district_id:
        qs = qs.filter(districtfk_id=district_id)  # adjust if different

    data = list(qs.values("id", "name").order_by("name"))
    return JsonResponse({"results": data})


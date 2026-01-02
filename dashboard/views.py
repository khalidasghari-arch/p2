# dashboard/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction

from hiva.models import (
    HQIPAssessment, Area, Section, Standards, Criteria,
    Facility
)
from hiva.models import Assessor, Implementor, Assessmenttype  # wherever these live

from dashboard.forms import AssessmentHeaderForm, AssessmentFormSet


def user_province(request):
    if request.user.is_superuser:
        return None
    profile = getattr(request.user, "profile", None)  # ✅ your related_name="profile"
    return getattr(profile, "province", None)


def facility_qs_for_user(request):
    if request.user.is_superuser:
        return Facility.objects.all()

    prov = user_province(request)
    if not prov:
        return Facility.objects.none()

    return Facility.objects.filter(districtfk__provincefk=prov)


@login_required
def hqip_start(request):
    facility_qs = facility_qs_for_user(request)

    if request.method == "POST":
        form = AssessmentHeaderForm(request.POST, facility_qs=facility_qs)
        if form.is_valid():
            cd = form.cleaned_data
            request.session["hqip_header"] = {
                "facilityfk": cd["facilityfk"].id,
                "assesorfk": cd["assesorfk"].id,
                "implementorfk": cd["implementorfk"].id,
                "assessmenttype": cd["assessmenttype"].id,
                "assessmentdate": str(cd["assessmentdate"]),
                "remarks": cd["remarks"] or "",
            }
            return redirect("hqip_area_list")
    else:
        form = AssessmentHeaderForm(facility_qs=facility_qs)

    return render(request, "dashboard/hqip/start.html", {"form": form})


@login_required
def hqip_area_list(request):
    header = request.session.get("hqip_header")
    if not header:
        return redirect("hqip_start")

    # ✅ enforce province restriction
    if not facility_qs_for_user(request).filter(id=header["facilityfk"]).exists():
        return redirect("hqip_start")

    areas = Area.objects.all().order_by("name")  # adjust if area field name differs
    return render(request, "dashboard/hqip/area_list.html", {"areas": areas, "header": header})


@login_required
def hqip_area_entry(request, area_id):
    header = request.session.get("hqip_header")
    if not header:
        return redirect("hqip_start")

    # ✅ enforce province restriction
    if not facility_qs_for_user(request).filter(id=header["facilityfk"]).exists():
        return redirect("hqip_start")

    area = get_object_or_404(Area, pk=area_id)

    # ✅ Criteria under this Area: Area -> Section -> Standards -> Criteria
    criteria_qs = Criteria.objects.filter(
        standardfk__sectionfk__areafk=area
    ).select_related(
        "standardfk",
        "standardfk__sectionfk",
    ).order_by(
        "standardfk__sectionfk__id",
        "standardfk__id",
        "id"
    )

    base_filter = dict(
        facilityfk_id=header["facilityfk"],
        assessmenttype_id=header["assessmenttype"],
        assessmentdate=header["assessmentdate"],
        assesorfk_id=header["assesorfk"],
        implementorfk_id=header["implementorfk"],
        areafk_id=area.id,
    )

    existing = Assessment.objects.filter(**base_filter)
    existing_criteria_ids = set(existing.values_list("criteriafk_id", flat=True))

    # ✅ create missing Assessment rows (1 row per Criteria)
    to_create = []
    for c in criteria_qs:
        if c.id in existing_criteria_ids:
            continue
        to_create.append(Assessment(
            areafk_id=area.id,
            sectionfk_id=c.standardfk.sectionfk_id if c.standardfk_id else None,
            standardfk_id=c.standardfk_id,
            criteriafk_id=c.id,
            scorefk_id=None,  # allow blank during entry
            assesorfk_id=header["assesorfk"],
            facilityfk_id=header["facilityfk"],
            implementorfk_id=header["implementorfk"],
            assessmenttype_id=header["assessmenttype"],
            assessmentdate=header["assessmentdate"],
            remarks=header.get("remarks", ""),
        ))

    with transaction.atomic():
        if to_create:
            Assessment.objects.bulk_create(to_create)

    rows_qs = Assessment.objects.filter(**base_filter).select_related(
        "sectionfk", "standardfk", "criteriafk", "scorefk"
    ).order_by(
        "sectionfk__id", "standardfk__id", "criteriafk__id"
    )

    if request.method == "POST":
        formset = AssessmentFormSet(request.POST, queryset=rows_qs)
        if formset.is_valid():
            formset.save()
            return redirect("hqip_area_list")
    else:
        formset = AssessmentFormSet(queryset=rows_qs)

    return render(request, "dashboard/hqip/area_entry.html", {
        "area": area,
        "header": header,
        "formset": formset,
    })

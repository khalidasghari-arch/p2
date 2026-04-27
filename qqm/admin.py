from django.contrib import admin, messages
from django.utils.html import format_html
from .models import (
    QQMUpload,
    QQMFacilityScore,
    QQMRawData,
    QQMStructuralDetail,
)
from qqm.services.importer import process_qqm_upload
from django.db.models import Q

def percent_display(value, colored=False):
    if value is None:
        return "-"

    try:
        percent = float(value) * 100
    except Exception:
        return "-"

    text = f"{percent:.2f}%"

    if not colored:
        return text

    if percent >= 70:
        color = "#198754"
    elif percent >= 50:
        color = "#fd7e14"
    else:
        color = "#dc3545"

    return format_html(
        '<span style="font-weight:700; color:{};">{}</span>',
        color,
        text,
    )

@admin.register(QQMUpload)
class QQMUploadAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "round_name",
        "uploaded_at",
        "status",
        "processed",
        "total_imported",
        "total_matched_facilities",
        "total_unmatched_facilities",
    )

    list_filter = ("round_name", "status", "processed")
    search_fields = ("title", "round_name")

    readonly_fields = (
        "uploaded_at",
        "processed",
        "status",
        "error_message",
        "total_imported",
        "total_matched_facilities",
        "total_unmatched_facilities",
    )

    actions = ["process_selected_uploads", "reset_selected_uploads"]

    fieldsets = (
        ("Upload Information", {
            "fields": ("title", "round_name", "excel_file")
        }),
        ("Processing Status", {
            "fields": (
                "uploaded_at",
                "status",
                "processed",
                "error_message",
                "total_imported",
                "total_matched_facilities",
                "total_unmatched_facilities",
            )
        }),
    )

    def process_selected_uploads(self, request, queryset):
        success = 0
        failed = 0

        for upload in queryset:
            try:
                result = process_qqm_upload(upload.id)
                success += 1
                self.message_user(
                    request,
                    (
                        f"{upload.title}: {result['message']} | "
                        f"Imported={result['imported']}, "
                        f"Matched={result['matched']}, "
                        f"Unmatched={result['unmatched']}"
                    ),
                    level=messages.SUCCESS,
                )
            except Exception as e:
                failed += 1
                self.message_user(
                    request,
                    f"{upload.title}: failed - {str(e)}",
                    level=messages.ERROR,
                )

        self.message_user(
            request,
            f"Completed. Success: {success}, Failed: {failed}",
            level=messages.INFO,
        )

    process_selected_uploads.short_description = "Process selected QQM uploads"

    def reset_selected_uploads(self, request, queryset):
        for upload in queryset:
            QQMFacilityScore.objects.filter(upload=upload).delete()
            upload.processed = False
            upload.status = "pending"
            upload.error_message = None
            upload.total_imported = 0
            upload.total_matched_facilities = 0
            upload.total_unmatched_facilities = 0
            upload.save()

        self.message_user(
            request,
            "Selected uploads were reset successfully.",
            level=messages.SUCCESS,
        )

    reset_selected_uploads.short_description = "Reset selected QQM uploads"

class QQMStructuralDetailInline(admin.StackedInline):
    model = QQMStructuralDetail
    can_delete = False
    extra = 0
    readonly_fields = (
        "d1_general_management_percent",
        "d2_hygiene_percent",
        "d3_opd_percent",
        "d4_fp_percent",
        "d5_lab_percent",
        "d6_drugs_percent",
        "d7_tracer_percent",
        "d8_maternity_percent",
        "d9_epi_percent",
        "d10_anc_percent",
    )

    fields = (
        "d1_general_management_percent",
        "d2_hygiene_percent",
        "d3_opd_percent",
        "d4_fp_percent",
        "d5_lab_percent",
        "d6_drugs_percent",
        "d7_tracer_percent",
        "d8_maternity_percent",
        "d9_epi_percent",
        "d10_anc_percent",
    )

    def d1_general_management_percent(self, obj):
        return percent_display(obj.d1_general_management, True)
    d1_general_management_percent.short_description = "Domain 1: General Management"

    def d2_hygiene_percent(self, obj):
        return percent_display(obj.d2_hygiene, True)
    d2_hygiene_percent.short_description = "Domain 2: Hygiene"

    def d3_opd_percent(self, obj):
        return percent_display(obj.d3_opd, True)
    d3_opd_percent.short_description = "Domain 3: OPD / Curative Consultations"

    def d4_fp_percent(self, obj):
        return percent_display(obj.d4_fp, True)
    d4_fp_percent.short_description = "Domain 4: Family Planning"

    def d5_lab_percent(self, obj):
        return percent_display(obj.d5_lab, True)
    d5_lab_percent.short_description = "Domain 5: Laboratory"

    def d6_drugs_percent(self, obj):
        return percent_display(obj.d6_drugs, True)
    d6_drugs_percent.short_description = "Domain 6: Essential Drugs Management"

    def d7_tracer_percent(self, obj):
        return percent_display(obj.d7_tracer, True)
    d7_tracer_percent.short_description = "Domain 7: Tracer Drugs"

    def d8_maternity_percent(self, obj):
        return percent_display(obj.d8_maternity, True)
    d8_maternity_percent.short_description = "Domain 8: Maternity"

    def d9_epi_percent(self, obj):
        return percent_display(obj.d9_epi, True)
    d9_epi_percent.short_description = "Domain 9: EPI"

    def d10_anc_percent(self, obj):
        return percent_display(obj.d10_anc, True)
    d10_anc_percent.short_description = "Domain 10: Antenatal Care"


@admin.register(QQMFacilityScore)
class QQMFacilityScoreAdmin(admin.ModelAdmin):
    list_display = (
        "hfname",
        "hfcode",

        "province",
        "district",
        "facility_type",

        "structural_percent",
        "outcome_percent",
        "content_percent",
        "qqm_percent",

        "upload",
    )

    list_filter = (
        "upload__round_name",
        "facility__districtfk__provincefk__name",
        "facility__districtfk__name",
        "facility__facilitytypefk__name",
    )

    search_fields = (
        "hfcode",
        "hfname_excel",
        "facility__name",
        "facility__districtfk__name",
        "facility__districtfk__provincefk__name",
    )

    list_select_related = (
        "facility",
        "facility__districtfk",
        "facility__districtfk__provincefk",
        "facility__facilitytypefk",
    )

    # -------- LOCATION FIELDS --------
    def province(self, obj):
        if obj.facility and obj.facility.districtfk and obj.facility.districtfk.provincefk:
            return obj.facility.districtfk.provincefk.name
        return "-"
    province.short_description = "Province"
    province.admin_order_field = "facility__districtfk__provincefk__name"

    def district(self, obj):
        if obj.facility and obj.facility.districtfk:
            return obj.facility.districtfk.name
        return "-"
    district.short_description = "District"
    district.admin_order_field = "facility__districtfk__name"

    def facility_type(self, obj):
        if obj.facility and obj.facility.facilitytypefk:
            return obj.facility.facilitytypefk.name
        return "-"
    facility_type.short_description = "Facility Type"
    facility_type.admin_order_field = "facility__facilitytypefk__name"

    # -------- EXISTING --------
    def hfname(self, obj):
        return obj.facility.name if obj.facility else obj.hfname_excel or "-"
    hfname.short_description = "Facility Name"
    hfname.admin_order_field = "hfname_excel"

    def hfcode(self, obj):
        return obj.hfcode
    hfcode.short_description = "HFCode"

    def structural_percent(self, obj):
        return percent_display(obj.structural_score, True)
    structural_percent.admin_order_field = "structural_score"

    def outcome_percent(self, obj):
        return percent_display(obj.outcome_score, True)
    outcome_percent.admin_order_field = "outcome_score"

    def content_percent(self, obj):
        return percent_display(obj.content_score, True)
    content_percent.admin_order_field = "content_score"

    def qqm_percent(self, obj):
        return percent_display(obj.qqm_score, True)
    qqm_percent.admin_order_field = "qqm_score"

class HasFacilityNameFilter(admin.SimpleListFilter):
    title = "Facility Name Status"
    parameter_name = "has_name"

    def lookups(self, request, model_admin):
        return (
            ("yes", "IQOC MNH HFs"),
            ("no", "NONE-IQOC MNH HFs"),
        )

    def queryset(self, request, queryset):
        has_name_q = (
            Q(score__facility__name__isnull=False)
            & ~Q(score__facility__name__exact="")
        ) | (
            Q(score__hfname_excel__isnull=False)
            & ~Q(score__hfname_excel__exact="")
        )

        if self.value() == "yes":
            return queryset.filter(has_name_q)

        if self.value() == "no":
            return queryset.exclude(has_name_q)

        return queryset

@admin.register(QQMStructuralDetail)
class QQMStructuralDetailAdmin(admin.ModelAdmin):
    list_display = (
        "province",
        "district",
        "hfname",
        "hfcode",
        "facility_type",
        "round_name",
        "d1_general_management_percent",
        "d2_hygiene_percent",
        "d3_opd_percent",
        "d4_fp_percent",
        "d5_lab_percent",
        "d6_drugs_percent",
        "d7_tracer_percent",
        "d8_maternity_percent",
        "d9_epi_percent",
        "d10_anc_percent",
    )

    list_filter = (
        "score__upload__round_name",
        HasFacilityNameFilter,
    )

    search_fields = (
        "score__hfcode",
        "score__hfname_excel",
        "score__facility__name",
    )

    ordering = ("score__hfname_excel",)
    list_per_page = 50

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related(
            "score",
            "score__facility",
            "score__upload",
        )

        has_name_q = (
            Q(score__facility__name__isnull=False)
            & ~Q(score__facility__name__exact="")
        ) | (
            Q(score__hfname_excel__isnull=False)
            & ~Q(score__hfname_excel__exact="")
        )

        if request.GET.get("has_name") is None:
            qs = qs.filter(has_name_q)

        return qs

    def percent(self, value):
        if value is None:
            return "-"
        try:
            return f"{float(value) * 100:.2f}%"
        except Exception:
            return "-"

    def hfname(self, obj):
        if obj.score.facility and obj.score.facility.name:
            return obj.score.facility.name
        return obj.score.hfname_excel or "-"
    hfname.short_description = "Facility Name"
    hfname.admin_order_field = "score__hfname_excel"

    def hfcode(self, obj):
        return obj.score.hfcode
    hfcode.short_description = "HFCode"
    hfcode.admin_order_field = "score__hfcode"

    def round_name(self, obj):
        return obj.score.upload.round_name
    round_name.short_description = "Round"
    round_name.admin_order_field = "score__upload__round_name"

    def d1_general_management_percent(self, obj):
        return self.percent(obj.d1_general_management)
    d1_general_management_percent.short_description = "D1 General"
    d1_general_management_percent.admin_order_field = "d1_general_management"

    def d2_hygiene_percent(self, obj):
        return self.percent(obj.d2_hygiene)
    d2_hygiene_percent.short_description = "D2 Hygiene"
    d2_hygiene_percent.admin_order_field = "d2_hygiene"

    def d3_opd_percent(self, obj):
        return self.percent(obj.d3_opd)
    d3_opd_percent.short_description = "D3 OPD"
    d3_opd_percent.admin_order_field = "d3_opd"

    def d4_fp_percent(self, obj):
        return self.percent(obj.d4_fp)
    d4_fp_percent.short_description = "D4 FP"
    d4_fp_percent.admin_order_field = "d4_fp"

    def d5_lab_percent(self, obj):
        return self.percent(obj.d5_lab)
    d5_lab_percent.short_description = "D5 Lab"
    d5_lab_percent.admin_order_field = "d5_lab"

    def d6_drugs_percent(self, obj):
        return self.percent(obj.d6_drugs)
    d6_drugs_percent.short_description = "D6 Drugs"
    d6_drugs_percent.admin_order_field = "d6_drugs"

    def d7_tracer_percent(self, obj):
        return self.percent(obj.d7_tracer)
    d7_tracer_percent.short_description = "D7 Tracer"
    d7_tracer_percent.admin_order_field = "d7_tracer"

    def d8_maternity_percent(self, obj):
        return self.percent(obj.d8_maternity)
    d8_maternity_percent.short_description = "D8 Maternity"
    d8_maternity_percent.admin_order_field = "d8_maternity"

    def d9_epi_percent(self, obj):
        return self.percent(obj.d9_epi)
    d9_epi_percent.short_description = "D9 EPI"
    d9_epi_percent.admin_order_field = "d9_epi"

    def d10_anc_percent(self, obj):
        return self.percent(obj.d10_anc)
    d10_anc_percent.short_description = "D10 ANC"
    d10_anc_percent.admin_order_field = "d10_anc"

    def province(self, obj):
        if obj.score.facility and obj.score.facility.districtfk and obj.score.facility.districtfk.provincefk:
            return obj.score.facility.districtfk.provincefk.name
        return "-"
    province.admin_order_field = "score__facility__districtfk__provincefk__name"


    def district(self, obj):
        if obj.score.facility and obj.score.facility.districtfk:
            return obj.score.facility.districtfk.name
        return "-"
    district.admin_order_field = "score__facility__districtfk__name"


    def facility_type(self, obj):
        if obj.score.facility and obj.score.facility.facilitytypefk:
            return obj.score.facility.facilitytypefk.name
        return "-"
    facility_type.admin_order_field = "score__facility__facilitytypefk__name"

@admin.register(QQMRawData)
class QQMRawDataAdmin(admin.ModelAdmin):
    list_display = ("score",)
    search_fields = ("score__hfcode", "score__hfname_excel")
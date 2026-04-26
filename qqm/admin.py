from django.contrib import admin, messages
from .models import QQMUpload, QQMFacilityScore, QQMRawData
from qqm.services.importer import process_qqm_upload
from django.utils.html import format_html


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


@admin.register(QQMFacilityScore)
class QQMFacilityScoreAdmin(admin.ModelAdmin):
    list_display = (
        "hfcode",
        #"hfname_excel",
        "facility",
        "structural_percent",
        "outcome_percent",
        "content_percent",
        "qqm_percent",
        "upload",
    )

    list_filter = ("upload__round_name", "upload__status")
    search_fields = (
        "hfcode",
        "hfname_excel",
        "facility__name",
    )

    readonly_fields = (
        "upload",
        "facility",
        "hfcode",
        "hfname_excel",
        "structural_score",
        "outcome_score",
        "content_score",
        "qqm_score",
        "structural_percent",
        "outcome_percent",
        "content_percent",
        "qqm_percent",
    )

    def format_percent(self, value):
        if value is None:
            return "-"
        return f"{value * 100:.2f}%"

    def structural_percent(self, obj):
        return self.format_percent(obj.structural_score)
    structural_percent.short_description = "Structural (%)"

    def outcome_percent(self, obj):
        return self.format_percent(obj.outcome_score)
    outcome_percent.short_description = "Outcome (%)"

    def content_percent(self, obj):
        return self.format_percent(obj.content_score)
    content_percent.short_description = "Content (%)"

    def qqm_percent(self, obj):
        if obj.qqm_score is None:
            return "-"

        percent = float(obj.qqm_score) * 100
        percent_text = f"{percent:.2f}%"

        if percent >= 70:
            color = "#198754"
        elif percent >= 50:
            color = "#fd7e14"
        else:
            color = "#dc3545"

        return format_html(
            '<span style="font-weight:600; color:{};">{}</span>',
            color,
            percent_text,
        )

    qqm_percent.short_description = "QQM (%)"


@admin.register(QQMRawData)
class QQMRawDataAdmin(admin.ModelAdmin):
    list_display = ("score",)
    search_fields = ("score__hfcode", "score__hfname_excel")
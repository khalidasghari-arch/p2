from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from hmis.models import HMISMonthlySummary
from hmis.models import HMISRawUpload, HMISFact
from hmis.services.pipeline import run_import

@admin.register(HMISRawUpload)
class HMISRawUploadAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "uploaded_at", "uploaded_by", "row_count", "hf_count", "period_min", "period_max")
    list_filter = ("status", "uploaded_at")
    actions = ("import_selected",)

    def import_selected(self, request, queryset):
        ok, failed = 0, 0
        for upload in queryset:
            try:
                run_import(upload)
                ok += 1
            except Exception as e:
                upload.status = "FAILED"
                upload.report = {"error": str(e)}
                upload.save(update_fields=["status", "report"])
                failed += 1
        self.message_user(request, f"Import: {ok} success, {failed} failed.", level=messages.INFO)

    import_selected.short_description = "Import selected HMIS uploads"


@admin.register(HMISFact)
class HMISFactAdmin(admin.ModelAdmin):
    # ✅ What users should see first (clean)
    list_display = (
        "prov", "dist", "hf",
        "year", "month", "month_name",
        "indicator_name", "value",
        "hiva_hfs",
    )

    # ✅ Sidebar filters (your request: HIVA-HFs in sidebar)
    list_filter = (
        "hiva_hfs",
        "prov",
        "year",
        "month",
        "indicator_name",
    )

    # ✅ Quick search
    search_fields = ("hf", "prov", "dist", "indicator_name")

    # ✅ Keep results ordered properly
    ordering = ("-year", "-month", "prov", "dist", "hf", "indicator_name")

    # ✅ Make admin faster with big data
    list_per_page = 50
    list_select_related = ("source_upload",)

    # ✅ Optional: quick navigation by year (works like date hierarchy)
    # If you want, keep this OFF because we have year/month filters already
    # date_hierarchy = "created_at"

    # ✅ Cleaner period display "YYYY-MM"
    @admin.display(description="Period")
    def period_readable(self, obj):
        # periodcode is YYYYMM; show YYYY-MM
        p = obj.periodcode or ""
        if len(p) == 6:
            return f"{p[:4]}-{p[4:6]}"
        return p

@admin.register(HMISMonthlySummary)
class HMISMonthlySummaryAdmin(admin.ModelAdmin):
    list_display = (
        "prov","dist","hf","year","month", "month_name",
        "hiva_hfs",
        "anc1","anc2","anc3","anc4",
        "pnc1","pnc2",
        "n_delivery","a_delivery","c_section",
        "lbw","stillbirth",
    )
    list_filter = ("hiva_hfs","prov","year","month")
    search_fields = ("hf","prov","dist")
    ordering = ("-year","-month","prov","dist","hf")

    @admin.display(description="Period")
    def period_readable(self, obj):
        p = obj.periodcode or ""
        return f"{p[:4]}-{p[4:6]}" if len(p) == 6 else p

from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from hmis.models import HMISRawUpload, HMISFact, IndicatorMetadata, HMISMonthlySummary
from hmis.services.pipeline import run_import
from calendar import month_name
from decimal import Decimal, ROUND_HALF_UP
from urllib.parse import urlencode
import openpyxl
from django.contrib import admin, messages
from django.db.models import Avg, Count, Max, Min, Sum
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.utils import timezone
from hmis.models import (
    HMISDashboard,
    HMISFact,
    HMISMonthlySummary,
    HMISRawUpload,
    IndicatorMetadata,
)
from hmis.services.pipeline import run_import
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from django.db.models import Avg, Count, Max, Min, Q, Sum

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

@admin.register(IndicatorMetadata)
class IndicatorMetadataAdmin(admin.ModelAdmin):
    list_display = (
        "indicator_code",
        "indicator_name",
        "indicator_short_name",
        "indicator_group",
        "indicator_domain",
        "is_active",
        "sort_order",
    )
    list_filter = ("indicator_group", "indicator_domain", "is_active")
    search_fields = ("indicator_code", "indicator_name", "indicator_short_name")
    ordering = ("sort_order", "indicator_name")

# ===========================================================================
# NEW HMIS PERFORMANCE DASHBOARD
# ===========================================================================


@admin.register(HMISDashboard)
class HMISDashboardAdmin(admin.ModelAdmin):
    """Read-only dashboard built from HMISMonthlySummary and HMISFact."""

    change_list_template = "admin/hmis/hmis_dashboard.html"

    INDICATORS = (
        ("anc1", "ANC 1st Visit"),
        ("anc2", "ANC 2nd Visit"),
        ("anc3", "ANC 3rd Visit"),
        ("anc4", "ANC 4th Visit"),
        ("pnc1", "PNC 1st Visit"),
        ("pnc2", "PNC 2nd Visit"),
        ("n_delivery", "Normal Deliveries"),
        ("a_delivery", "Assisted Deliveries"),
        ("c_section", "C-sections"),
        ("lbw", "Low Birth Weight"),
        ("stillbirth", "Stillbirths"),
    )
    INDICATOR_LABELS = dict(INDICATORS)
    INDICATOR_FIELDS = tuple(field for field, _label in INDICATORS)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        opts = HMISMonthlySummary._meta
        return (
            request.user.is_superuser
            or request.user.has_perm(f"{opts.app_label}.view_{opts.model_name}")
            or request.user.has_perm(f"{opts.app_label}.change_{opts.model_name}")
        )

    def has_module_permission(self, request):
        return self.has_view_permission(request)

    @staticmethod
    def _decimal(value):
        return Decimal("0") if value is None else Decimal(str(value))

    @staticmethod
    def _round2(value):
        if value is None:
            return None
        return float(
            Decimal(str(value)).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )
        )

    def _percent(self, numerator, denominator):
        denominator = self._decimal(denominator)
        if denominator == 0:
            return None
        value = self._decimal(numerator) / denominator * Decimal("100")
        return self._round2(value)

    def _rate_per_1000(self, numerator, denominator):
        denominator = self._decimal(denominator)
        if denominator == 0:
            return None
        value = self._decimal(numerator) / denominator * Decimal("1000")
        return self._round2(value)

    @staticmethod
    def _period_label(periodcode):
        period = str(periodcode or "")
        if len(period) == 6 and period.isdigit():
            month_number = int(period[4:6])
            if 1 <= month_number <= 12:
                return f"{month_name[month_number]} {period[:4]}"
        return period or "Not available"

    @staticmethod
    def _number_display(value, decimals=0):
        if value is None:
            return "—"
        number = float(value)
        if decimals == 0:
            return f"{number:,.0f}"
        return f"{number:,.{decimals}f}"

    @staticmethod
    def _percent_display(value):
        return "—" if value is None else f"{float(value):,.2f}%"

    @staticmethod
    def _rate_display(value):
        return "—" if value is None else f"{float(value):,.2f}"

    def _read_filters(self, request):
        indicator = (request.GET.get("indicator") or "anc1").strip()
        if indicator not in self.INDICATOR_LABELS:
            indicator = "anc1"

        facility_group = (request.GET.get("facility_group") or "all").strip()
        if facility_group not in {"all", "hiva", "non_hiva"}:
            facility_group = "all"

        year_value = (request.GET.get("year") or "").strip()
        month_value = (request.GET.get("month") or "").strip()

        try:
            selected_year = int(year_value) if year_value else None
        except (TypeError, ValueError):
            selected_year = None

        try:
            selected_month = int(month_value) if month_value else None
        except (TypeError, ValueError):
            selected_month = None
        if selected_month not in range(1, 13):
            selected_month = None

        return {
            "prov": (request.GET.get("prov") or "").strip(),
            "dist": (request.GET.get("dist") or "").strip(),
            "hf": (request.GET.get("hf") or "").strip(),
            "year": selected_year,
            "month": selected_month,
            "facility_group": facility_group,
            "indicator": indicator,
        }

    def _filter_queryset(self, queryset, filters):
        if filters["prov"]:
            queryset = queryset.filter(prov=filters["prov"])
        if filters["dist"]:
            queryset = queryset.filter(dist=filters["dist"])
        if filters["hf"]:
            queryset = queryset.filter(hf=filters["hf"])
        if filters["year"] is not None:
            queryset = queryset.filter(year=filters["year"])
        if filters["month"] is not None:
            queryset = queryset.filter(month=filters["month"])
        if filters["facility_group"] == "hiva":
            queryset = queryset.filter(hiva_hfs=True)
        elif filters["facility_group"] == "non_hiva":
            queryset = queryset.filter(hiva_hfs=False)
        return queryset

    @staticmethod
    def _apply_facility_group(queryset, facility_group):
        """Limit either HMIS table to the selected facility group."""
        if facility_group == "hiva":
            return queryset.filter(hiva_hfs=True)
        if facility_group == "non_hiva":
            return queryset.filter(hiva_hfs=False)
        return queryset

    def _filter_options(self, base_queryset, filters):
        # Facility Group is the first level of the location cascade:
        # Facility Group -> Province -> District -> Health Facility.
        group_queryset = self._apply_facility_group(
            base_queryset,
            filters["facility_group"],
        )

        provinces = list(
            group_queryset.exclude(prov="")
            .values_list("prov", flat=True)
            .distinct()
            .order_by("prov")
        )

        district_queryset = group_queryset
        if filters["prov"]:
            district_queryset = district_queryset.filter(prov=filters["prov"])
        districts = list(
            district_queryset.exclude(dist="")
            .values_list("dist", flat=True)
            .distinct()
            .order_by("dist")
        )

        facility_queryset = district_queryset
        if filters["dist"]:
            facility_queryset = facility_queryset.filter(dist=filters["dist"])
        facilities = list(
            facility_queryset.exclude(hf="")
            .values_list("hf", flat=True)
            .distinct()
            .order_by("hf")
        )

        period_queryset = facility_queryset
        if filters["hf"]:
            period_queryset = period_queryset.filter(hf=filters["hf"])

        years = list(
            period_queryset.values_list("year", flat=True)
            .distinct()
            .order_by("-year")
        )

        month_queryset = period_queryset
        if filters["year"] is not None:
            month_queryset = month_queryset.filter(year=filters["year"])
        month_numbers = list(
            month_queryset.values_list("month", flat=True)
            .distinct()
            .order_by("month")
        )
        months = [
            {"value": value, "label": month_name[value]}
            for value in month_numbers
            if value in range(1, 13)
        ]

        # A compact, distinct hierarchy lets the browser update the dependent
        # dropdowns immediately without reloading the chart-heavy dashboard.
        location_cascade = [
            {
                "group": "hiva" if row["hiva_hfs"] else "non_hiva",
                "province": row["prov"],
                "district": row["dist"],
                "facility": row["hf"],
            }
            for row in (
                base_queryset.exclude(prov="")
                .exclude(dist="")
                .exclude(hf="")
                .values("hiva_hfs", "prov", "dist", "hf")
                .distinct()
                .order_by("hiva_hfs", "prov", "dist", "hf")
            )
        ]

        return {
            "provinces": provinces,
            "districts": districts,
            "facilities": facilities,
            "years": years,
            "months": months,
            "location_cascade": location_cascade,
        }

    def _filter_fact_queryset(self, queryset, filters):
        """Apply the dashboard filters to the long-format HMIS indicator table."""
        if filters["prov"]:
            queryset = queryset.filter(prov=filters["prov"])
        if filters["dist"]:
            queryset = queryset.filter(dist=filters["dist"])
        if filters["hf"]:
            queryset = queryset.filter(hf=filters["hf"])
        if filters["year"] is not None:
            queryset = queryset.filter(year=filters["year"])
        if filters["month"] is not None:
            queryset = queryset.filter(month=filters["month"])
        if filters["facility_group"] == "hiva":
            queryset = queryset.filter(hiva_hfs=True)
        elif filters["facility_group"] == "non_hiva":
            queryset = queryset.filter(hiva_hfs=False)
        return queryset

    def _all_hmis_indicator_trends(self, queryset):
        """Build one monthly trend chart for every indicator in HMISFact."""
        available_periods = list(
            queryset.exclude(periodcode="")
            .values_list("periodcode", flat=True)
            .distinct()
            .order_by("periodcode")
        )

        metadata = {}
        for item in (
            IndicatorMetadata.objects.all()
            .order_by("-is_active", "sort_order", "indicator_name")
            .values(
                "indicator_code",
                "indicator_name",
                "indicator_short_name",
                "indicator_group",
                "indicator_domain",
                "sort_order",
            )
        ):
            metadata.setdefault(item["indicator_code"], item)

        grouped = (
            queryset.values("indicator_code", "periodcode")
            .annotate(
                # Do not reuse a model-field name as an aggregate alias.
                # Django 5.1 can resolve a later expression to that alias
                # instead of to the original database column.
                indicator_name_max=Max("indicator_name"),
                total=Sum("value"),
                reported_values=Count("value"),
            )
            .order_by("indicator_code", "periodcode")
        )

        indicators = {}
        for item in grouped:
            code = item["indicator_code"] or "Not coded"
            meta = metadata.get(code, {})
            indicator = indicators.setdefault(
                code,
                {
                    "code": code,
                    "title": (
                        meta.get("indicator_short_name")
                        or meta.get("indicator_name")
                        or item["indicator_name_max"]
                        or code
                    ),
                    "full_name": (
                        meta.get("indicator_name")
                        or item["indicator_name_max"]
                        or code
                    ),
                    "group": meta.get("indicator_group") or "Not classified",
                    "domain": meta.get("indicator_domain") or "Not classified",
                    "sort_order": meta.get("sort_order"),
                    "values_by_period": {},
                },
            )
            indicator["values_by_period"][item["periodcode"]] = (
                float(item["total"])
                if item["reported_values"] and item["total"] is not None
                else None
            )

        ordered = sorted(
            indicators.values(),
            key=lambda item: (
                item["sort_order"] is None,
                item["sort_order"] if item["sort_order"] is not None else 0,
                item["title"].lower(),
                item["code"],
            ),
        )
        palette = (
            "#174f78",
            "#2e7d32",
            "#6a3d9a",
            "#00796b",
            "#ef6c00",
            "#c62828",
            "#455a64",
            "#8d6e63",
        )
        cards = []
        charts = []
        for index, indicator in enumerate(ordered, start=1):
            chart_id = f"allHmisIndicatorTrendChart{index}"
            cards.append(
                {
                    "chart_id": chart_id,
                    "indicator_code": indicator["code"],
                    "title": indicator["title"],
                    "full_name": indicator["full_name"],
                    "group": indicator["group"],
                    "domain": indicator["domain"],
                    "period_count": sum(
                        value is not None
                        for value in indicator["values_by_period"].values()
                    ),
                    "search_text": " ".join(
                        str(value)
                        for value in (
                            indicator["code"],
                            indicator["title"],
                            indicator["full_name"],
                            indicator["group"],
                            indicator["domain"],
                        )
                    ).lower(),
                }
            )
            charts.append(
                {
                    "id": chart_id,
                    "labels": [
                        self._period_label(periodcode)
                        for periodcode in available_periods
                    ],
                    "datasets": [
                        {
                            "label": indicator["title"],
                            "data": [
                                indicator["values_by_period"].get(periodcode)
                                for periodcode in available_periods
                            ],
                            "color": palette[(index - 1) % len(palette)],
                        }
                    ],
                }
            )
        return cards, charts

    def _summary_aggregate(self, queryset):
        expressions = {
            "reporting_records": Count("id"),
            "facilities": Count("hf", distinct=True),
            "periods": Count("periodcode", distinct=True),
            "period_min": Min("periodcode"),
            "period_max": Max("periodcode"),
        }
        for field in self.INDICATOR_FIELDS:
            expressions[f"{field}_total"] = Sum(field)
            expressions[f"{field}_reported"] = Count(field)
        return queryset.aggregate(**expressions)

    def _monthly_rows(self, queryset, selected_indicator):
        annotations = {
            "reporting_records": Count("id"),
            "facility_count": Count("hf", distinct=True),
        }
        for field in self.INDICATOR_FIELDS:
            # Use an alias that cannot shadow the real model field.  Using
            # ``anc1=Sum("anc1")`` followed by ``Count("anc1")`` in this
            # same annotate() call makes Django treat Count's anc1 as the
            # aggregate alias, causing "anc1 is an aggregate".
            annotations[f"{field}_total"] = Sum(field)
            annotations[f"{field}_reported"] = Count(field)

        rows = []
        grouped = queryset.values("periodcode").annotate(**annotations).order_by(
            "periodcode"
        )
        for item in grouped:
            row = {
                "periodcode": item["periodcode"],
                "period": self._period_label(item["periodcode"]),
                "reporting_records": item["reporting_records"],
                "facility_count": item["facility_count"],
            }
            for field in self.INDICATOR_FIELDS:
                total_key = f"{field}_total"
                row[field] = self._decimal(item[total_key])
                row[f"{field}_display"] = self._number_display(item[total_key])
            row["selected_total"] = row[selected_indicator]
            row["selected_total_display"] = self._number_display(
                row["selected_total"]
            )
            row["total_deliveries"] = (
                row["n_delivery"] + row["a_delivery"] + row["c_section"]
            )
            row["total_deliveries_display"] = self._number_display(
                row["total_deliveries"]
            )
            row["c_section_rate"] = self._percent(
                row["c_section"], row["total_deliveries"]
            )
            row["c_section_rate_display"] = self._percent_display(
                row["c_section_rate"]
            )
            rows.append(row)
        return rows

    def _facility_monthly_export_rows(self, queryset):
        """Return facility-month rows for Excel without creating dashboard charts."""
        annotations = {}
        for field in self.INDICATOR_FIELDS:
            annotations[f"{field}_total"] = Sum(field)
            annotations[f"{field}_reported"] = Count(field)

        grouped = (
            queryset.values(
                "prov",
                "dist",
                "hf",
                "hfid",
                "hiva_hfs",
                "periodcode",
            )
            .annotate(**annotations)
            .order_by("prov", "dist", "hf", "periodcode")
        )

        rows = []
        for item in grouped:
            values = {
                field: (
                    float(item[f"{field}_total"])
                    if item[f"{field}_reported"]
                    and item[f"{field}_total"] is not None
                    else None
                )
                for field in self.INDICATOR_FIELDS
            }
            rows.append(
                {
                    "province": item["prov"] or "Not specified",
                    "district": item["dist"] or "Not specified",
                    "facility": item["hf"] or "Not specified",
                    "hfid": item["hfid"],
                    "hiva_hfs": item["hiva_hfs"],
                    "periodcode": item["periodcode"],
                    "period": self._period_label(item["periodcode"]),
                    **values,
                }
            )
        return rows

    def _province_rows(self, queryset, selected_indicator):
        grouped = (
            queryset.values("prov")
            .annotate(
                reporting_records=Count("id"),
                facility_count=Count("hf", distinct=True),
                selected_total=Sum(selected_indicator),
                selected_average=Avg(selected_indicator),
                anc1_total=Sum("anc1"),
                anc4_total=Sum("anc4"),
                normal_total=Sum("n_delivery"),
                assisted_total=Sum("a_delivery"),
                c_section_total=Sum("c_section"),
                lbw_total=Sum("lbw"),
                stillbirth_total=Sum("stillbirth"),
            )
            .order_by("prov")
        )

        rows = []
        for item in grouped:
            deliveries = (
                self._decimal(item["normal_total"])
                + self._decimal(item["assisted_total"])
                + self._decimal(item["c_section_total"])
            )
            selected_total = self._decimal(item["selected_total"])
            anc_ratio = self._percent(item["anc4_total"], item["anc1_total"])
            c_section_rate = self._percent(item["c_section_total"], deliveries)
            stillbirth_rate = self._rate_per_1000(
                item["stillbirth_total"], deliveries
            )
            rows.append(
                {
                    "province": item["prov"] or "Not specified",
                    "reporting_records": item["reporting_records"],
                    "facility_count": item["facility_count"],
                    "selected_total": selected_total,
                    "selected_total_display": self._number_display(selected_total),
                    "selected_average": self._round2(item["selected_average"]),
                    "selected_average_display": self._number_display(
                        item["selected_average"], 2
                    ),
                    "anc4_ratio": anc_ratio,
                    "anc4_ratio_display": self._percent_display(anc_ratio),
                    "total_deliveries": deliveries,
                    "total_deliveries_display": self._number_display(deliveries),
                    "c_section_rate": c_section_rate,
                    "c_section_rate_display": self._percent_display(
                        c_section_rate
                    ),
                    "lbw_total": self._decimal(item["lbw_total"]),
                    "lbw_total_display": self._number_display(item["lbw_total"]),
                    "stillbirth_total": self._decimal(item["stillbirth_total"]),
                    "stillbirth_total_display": self._number_display(
                        item["stillbirth_total"]
                    ),
                    "stillbirth_rate": stillbirth_rate,
                    "stillbirth_rate_display": self._rate_display(stillbirth_rate),
                }
            )
        rows.sort(key=lambda row: row["selected_total"], reverse=True)
        return rows

    def _facility_rows(self, queryset, selected_indicator):
        grouped = (
            queryset.values("prov", "dist", "hf", "hfid", "hiva_hfs")
            .annotate(
                reporting_records=Count("id"),
                period_min=Min("periodcode"),
                period_max=Max("periodcode"),
                selected_total=Sum(selected_indicator),
                selected_average=Avg(selected_indicator),
                anc1_total=Sum("anc1"),
                anc4_total=Sum("anc4"),
                normal_total=Sum("n_delivery"),
                assisted_total=Sum("a_delivery"),
                c_section_total=Sum("c_section"),
                lbw_total=Sum("lbw"),
                stillbirth_total=Sum("stillbirth"),
            )
            .order_by("prov", "dist", "hf")
        )

        rows = []
        for item in grouped:
            deliveries = (
                self._decimal(item["normal_total"])
                + self._decimal(item["assisted_total"])
                + self._decimal(item["c_section_total"])
            )
            selected_total = self._decimal(item["selected_total"])
            anc_ratio = self._percent(item["anc4_total"], item["anc1_total"])
            c_section_rate = self._percent(item["c_section_total"], deliveries)
            stillbirth_rate = self._rate_per_1000(
                item["stillbirth_total"], deliveries
            )
            rows.append(
                {
                    "province": item["prov"] or "Not specified",
                    "district": item["dist"] or "Not specified",
                    "facility": item["hf"] or "Not specified",
                    "hfid": item["hfid"],
                    "hiva_hfs": item["hiva_hfs"],
                    "facility_group": "HIVA HF"
                    if item["hiva_hfs"]
                    else "Non-HIVA HF",
                    "reporting_records": item["reporting_records"],
                    "period_min": item["period_min"] or "",
                    "period_max": item["period_max"] or "",
                    "selected_total": selected_total,
                    "selected_total_display": self._number_display(selected_total),
                    "selected_average": self._round2(item["selected_average"]),
                    "selected_average_display": self._number_display(
                        item["selected_average"], 2
                    ),
                    "anc4_ratio": anc_ratio,
                    "anc4_ratio_display": self._percent_display(anc_ratio),
                    "total_deliveries": deliveries,
                    "total_deliveries_display": self._number_display(deliveries),
                    "c_section_rate": c_section_rate,
                    "c_section_rate_display": self._percent_display(
                        c_section_rate
                    ),
                    "lbw_total": self._decimal(item["lbw_total"]),
                    "lbw_total_display": self._number_display(item["lbw_total"]),
                    "stillbirth_total": self._decimal(item["stillbirth_total"]),
                    "stillbirth_total_display": self._number_display(
                        item["stillbirth_total"]
                    ),
                    "stillbirth_rate": stillbirth_rate,
                    "stillbirth_rate_display": self._rate_display(stillbirth_rate),
                }
            )
        rows.sort(key=lambda row: row["selected_total"], reverse=True)
        for rank, row in enumerate(rows, start=1):
            row["rank"] = rank
        return rows

    def _build_dashboard_data(self, queryset, selected_indicator):
        summary = self._summary_aggregate(queryset)
        totals = {
            field: self._decimal(summary[f"{field}_total"])
            for field in self.INDICATOR_FIELDS
        }

        reporting_records = summary["reporting_records"] or 0
        facilities = summary["facilities"] or 0
        periods = summary["periods"] or 0
        possible_cells = reporting_records * len(self.INDICATOR_FIELDS)
        reported_cells = sum(
            summary[f"{field}_reported"] or 0 for field in self.INDICATOR_FIELDS
        )
        data_completeness = self._percent(reported_cells, possible_cells)

        total_deliveries = (
            totals["n_delivery"]
            + totals["a_delivery"]
            + totals["c_section"]
        )
        anc4_ratio = self._percent(totals["anc4"], totals["anc1"])
        pnc2_ratio = self._percent(totals["pnc2"], totals["pnc1"])
        c_section_rate = self._percent(totals["c_section"], total_deliveries)
        stillbirth_rate = self._rate_per_1000(
            totals["stillbirth"], total_deliveries
        )

        monthly_rows = self._monthly_rows(queryset, selected_indicator)
        province_rows = self._province_rows(queryset, selected_indicator)
        facility_rows = self._facility_rows(queryset, selected_indicator)
        facility_monthly_rows = self._facility_monthly_export_rows(queryset)

        selected_label = self.INDICATOR_LABELS[selected_indicator]
        period_min = summary["period_min"]
        period_max = summary["period_max"]
        if period_min and period_max:
            period_range = (
                self._period_label(period_min)
                if period_min == period_max
                else f"{self._period_label(period_min)} to {self._period_label(period_max)}"
            )
        else:
            period_range = "No reporting period available"

        kpis = [
            {
                "label": "Reporting Records",
                "value": self._number_display(reporting_records),
                "help": "Facility-month summary records",
                "class": "primary",
            },
            {
                "label": "Health Facilities",
                "value": self._number_display(facilities),
                "help": "Distinct reporting facilities",
                "class": "blue",
            },
            {
                "label": "Reporting Periods",
                "value": self._number_display(periods),
                "help": period_range,
                "class": "blue",
            },
            {
                "label": "Data Completeness",
                "value": self._percent_display(data_completeness),
                "help": "Non-blank cells across the 11 summary indicators",
                "class": "green",
            },
            {
                "label": "ANC 1st Visit",
                "value": self._number_display(totals["anc1"]),
                "help": "Total reported ANC1 services",
                "class": "purple",
            },
            {
                "label": "ANC 4th Visit",
                "value": self._number_display(totals["anc4"]),
                "help": f"ANC4-to-ANC1 ratio: {self._percent_display(anc4_ratio)}",
                "class": "purple",
            },
            {
                "label": "PNC 1st Visit",
                "value": self._number_display(totals["pnc1"]),
                "help": f"PNC2-to-PNC1 ratio: {self._percent_display(pnc2_ratio)}",
                "class": "teal",
            },
            {
                "label": "Total Deliveries",
                "value": self._number_display(total_deliveries),
                "help": "Normal + assisted + C-section",
                "class": "green",
            },
            {
                "label": "C-section Rate",
                "value": self._percent_display(c_section_rate),
                "help": "C-sections divided by total reported deliveries",
                "class": "orange",
            },
            {
                "label": "Stillbirths",
                "value": self._number_display(totals["stillbirth"]),
                "help": f"{self._rate_display(stillbirth_rate)} per 1,000 reported deliveries",
                "class": "red",
            },
        ]

        chart_data = {"all_hmis_indicator_trends": []}

        return {
            "summary": summary,
            "totals": totals,
            "kpis": kpis,
            "period_range": period_range,
            "selected_indicator": selected_indicator,
            "selected_indicator_label": selected_label,
            "data_completeness": data_completeness,
            "total_deliveries": total_deliveries,
            "anc4_ratio": anc4_ratio,
            "pnc2_ratio": pnc2_ratio,
            "c_section_rate": c_section_rate,
            "stillbirth_rate": stillbirth_rate,
            "monthly_rows": monthly_rows,
            "province_rows": province_rows,
            "facility_rows": facility_rows,
            "facility_monthly_rows": facility_monthly_rows,
            "chart_data": chart_data,
        }

    @staticmethod
    def _style_worksheet(worksheet, freeze="A2"):
        header_fill = PatternFill("solid", fgColor="1F4E78")
        header_font = Font(color="FFFFFF", bold=True)
        thin = Side(style="thin", color="D9E2F3")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)

        for cell in worksheet[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = border
        for row in worksheet.iter_rows(min_row=2):
            for cell in row:
                cell.border = border
                cell.alignment = Alignment(vertical="top")
        worksheet.freeze_panes = freeze
        if worksheet.max_row >= 2 and worksheet.max_column >= 1:
            worksheet.auto_filter.ref = worksheet.dimensions
        for column_cells in worksheet.columns:
            length = max(
                len(str(cell.value)) if cell.value is not None else 0
                for cell in column_cells
            )
            letter = get_column_letter(column_cells[0].column)
            worksheet.column_dimensions[letter].width = min(max(length + 2, 12), 42)

    def _export_excel(self, data, filters):
        workbook = openpyxl.Workbook()
        workbook.remove(workbook.active)

        summary_sheet = workbook.create_sheet("Dashboard Summary")
        summary_sheet.append(["HMIS PERFORMANCE DASHBOARD", ""])
        summary_sheet.append(["Generated", timezone.localtime().strftime("%Y-%m-%d %H:%M")])
        summary_sheet.append(["Province", filters["prov"] or "All"])
        summary_sheet.append(["District", filters["dist"] or "All"])
        summary_sheet.append(["Health Facility", filters["hf"] or "All"])
        summary_sheet.append(["Year", filters["year"] or "All"])
        summary_sheet.append(["Month", month_name[filters["month"]] if filters["month"] else "All"])
        group_label = {
            "all": "All facilities",
            "hiva": "HIVA health facilities",
            "non_hiva": "Non-HIVA health facilities",
        }[filters["facility_group"]]
        summary_sheet.append(["Facility Group", group_label])
        summary_sheet.append(["Selected Indicator", data["selected_indicator_label"]])
        summary_sheet.append(["Reporting Period", data["period_range"]])
        summary_sheet.append([])
        summary_sheet.append(["KPI", "Result", "Definition"])
        for kpi in data["kpis"]:
            summary_sheet.append([kpi["label"], kpi["value"], kpi["help"]])
        summary_sheet.merge_cells("A1:B1")
        summary_sheet["A1"].fill = PatternFill("solid", fgColor="1F4E78")
        summary_sheet["A1"].font = Font(color="FFFFFF", bold=True, size=16)
        summary_sheet["A1"].alignment = Alignment(horizontal="center")
        for cell in summary_sheet[12]:
            cell.fill = PatternFill("solid", fgColor="5B9BD5")
            cell.font = Font(color="FFFFFF", bold=True)
        summary_sheet.column_dimensions["A"].width = 28
        summary_sheet.column_dimensions["B"].width = 28
        summary_sheet.column_dimensions["C"].width = 55

        monthly_sheet = workbook.create_sheet("Monthly Results")
        monthly_headers = [
            "Period Code",
            "Period",
            "Reporting Records",
            "Health Facilities",
        ] + [label for _field, label in self.INDICATORS] + [
            "Total Deliveries",
            "C-section Rate (%)",
        ]
        monthly_sheet.append(monthly_headers)
        for row in data["monthly_rows"]:
            monthly_sheet.append(
                [
                    row["periodcode"],
                    row["period"],
                    row["reporting_records"],
                    row["facility_count"],
                ]
                + [float(row[field]) for field in self.INDICATOR_FIELDS]
                + [
                    float(row["total_deliveries"]),
                    row["c_section_rate"],
                ]
            )
        self._style_worksheet(monthly_sheet)

        facility_monthly_sheet = workbook.create_sheet("Facility Monthly Trends")
        facility_monthly_sheet.append(
            [
                "Province",
                "District",
                "Health Facility",
                "HF ID",
                "Facility Group",
                "Period Code",
                "Period",
            ]
            + [label for _field, label in self.INDICATORS]
        )
        for row in data["facility_monthly_rows"]:
            facility_monthly_sheet.append(
                [
                    row["province"],
                    row["district"],
                    row["facility"],
                    row["hfid"],
                    "HIVA HF" if row["hiva_hfs"] else "Non-HIVA HF",
                    row["periodcode"],
                    row["period"],
                ]
                + [row[field] for field in self.INDICATOR_FIELDS]
            )
        self._style_worksheet(facility_monthly_sheet)

        all_indicator_sheet = workbook.create_sheet("All Indicator Trends")
        all_indicator_sheet.append(
            [
                "Indicator Code",
                "Indicator Name",
                "Indicator Group",
                "Indicator Domain",
                "Reporting Month",
                "Reported Total",
            ]
        )
        all_indicator_charts = {
            chart["id"]: chart
            for chart in data["chart_data"].get("all_hmis_indicator_trends", [])
        }
        for card in data.get("all_hmis_indicator_cards", []):
            chart = all_indicator_charts.get(card["chart_id"])
            if not chart or not chart["datasets"]:
                continue
            values = chart["datasets"][0]["data"]
            for period, value in zip(chart["labels"], values):
                all_indicator_sheet.append(
                    [
                        card["indicator_code"],
                        card["full_name"],
                        card["group"],
                        card["domain"],
                        period,
                        value,
                    ]
                )
        self._style_worksheet(all_indicator_sheet)

        province_sheet = workbook.create_sheet("Province Results")
        province_sheet.append(
            [
                "Province",
                "Health Facilities",
                "Reporting Records",
                f"{data['selected_indicator_label']} Total",
                f"{data['selected_indicator_label']} Average per Report",
                "ANC4 / ANC1 (%)",
                "Total Deliveries",
                "C-section Rate (%)",
                "Low Birth Weight",
                "Stillbirths",
                "Stillbirths per 1,000 Deliveries",
            ]
        )
        for row in data["province_rows"]:
            province_sheet.append(
                [
                    row["province"],
                    row["facility_count"],
                    row["reporting_records"],
                    float(row["selected_total"]),
                    row["selected_average"],
                    row["anc4_ratio"],
                    float(row["total_deliveries"]),
                    row["c_section_rate"],
                    float(row["lbw_total"]),
                    float(row["stillbirth_total"]),
                    row["stillbirth_rate"],
                ]
            )
        self._style_worksheet(province_sheet)

        facility_sheet = workbook.create_sheet("Facility Results")
        facility_sheet.append(
            [
                "Rank",
                "Province",
                "District",
                "Health Facility",
                "HF ID",
                "Facility Group",
                "Reporting Records",
                "Start Period",
                "End Period",
                f"{data['selected_indicator_label']} Total",
                f"{data['selected_indicator_label']} Average per Report",
                "ANC4 / ANC1 (%)",
                "Total Deliveries",
                "C-section Rate (%)",
                "Low Birth Weight",
                "Stillbirths",
                "Stillbirths per 1,000 Deliveries",
            ]
        )
        for row in data["facility_rows"]:
            facility_sheet.append(
                [
                    row["rank"],
                    row["province"],
                    row["district"],
                    row["facility"],
                    row["hfid"],
                    row["facility_group"],
                    row["reporting_records"],
                    row["period_min"],
                    row["period_max"],
                    float(row["selected_total"]),
                    row["selected_average"],
                    row["anc4_ratio"],
                    float(row["total_deliveries"]),
                    row["c_section_rate"],
                    float(row["lbw_total"]),
                    float(row["stillbirth_total"]),
                    row["stillbirth_rate"],
                ]
            )
        self._style_worksheet(facility_sheet)

        response = HttpResponse(
            content_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        )
        timestamp = timezone.localtime().strftime("%Y%m%d_%H%M%S")
        response["Content-Disposition"] = (
            f'attachment; filename="HMIS_Performance_Dashboard_{timestamp}.xlsx"'
        )
        workbook.save(response)
        return response

    def changelist_view(self, request, extra_context=None):
        filters = self._read_filters(request)
        base_queryset = HMISMonthlySummary.objects.all()
        options = self._filter_options(base_queryset, filters)
        queryset = self._filter_queryset(base_queryset, filters)
        data = self._build_dashboard_data(queryset, filters["indicator"])
        fact_queryset = self._filter_fact_queryset(HMISFact.objects.all(), filters)
        all_indicator_cards, all_indicator_charts = (
            self._all_hmis_indicator_trends(fact_queryset)
        )
        data["all_hmis_indicator_cards"] = all_indicator_cards
        data["chart_data"]["all_hmis_indicator_trends"] = all_indicator_charts

        if request.GET.get("export") == "xlsx":
            return self._export_excel(data, filters)

        query_parameters = []
        for key in (
            "prov",
            "dist",
            "hf",
            "year",
            "month",
            "facility_group",
            "indicator",
        ):
            value = filters[key]
            if value not in (None, "", "all"):
                query_parameters.append((key, value))
        export_parameters = query_parameters + [("export", "xlsx")]

        context = {
            **self.admin_site.each_context(request),
            "title": "HMIS Performance Dashboard",
            "opts": self.model._meta,
            "filters": filters,
            "filter_options": options,
            "indicator_options": self.INDICATORS,
            "export_url": f"?{urlencode(export_parameters)}",
            **data,
        }
        if extra_context:
            context.update(extra_context)
        request.current_app = self.admin_site.name
        return TemplateResponse(request, self.change_list_template, context)
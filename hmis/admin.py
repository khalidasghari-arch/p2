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

        comparison_period = (request.GET.get("comparison_period") or "").strip()
        if not self._is_valid_periodcode(comparison_period):
            comparison_period = ""

        return {
            "prov": (request.GET.get("prov") or "").strip(),
            "dist": (request.GET.get("dist") or "").strip(),
            "hf": (request.GET.get("hf") or "").strip(),
            "year": selected_year,
            "month": selected_month,
            "facility_group": facility_group,
            "indicator": indicator,
            "comparison_period": comparison_period,
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

    def _filter_options(self, base_queryset, filters):
        provinces = list(
            base_queryset.exclude(prov="")
            .values_list("prov", flat=True)
            .distinct()
            .order_by("prov")
        )

        district_queryset = base_queryset
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
        if filters["facility_group"] == "hiva":
            period_queryset = period_queryset.filter(hiva_hfs=True)
        elif filters["facility_group"] == "non_hiva":
            period_queryset = period_queryset.filter(hiva_hfs=False)

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

        return {
            "provinces": provinces,
            "districts": districts,
            "facilities": facilities,
            "years": years,
            "months": months,
        }

    @staticmethod
    def _is_valid_periodcode(periodcode):
        period = str(periodcode or "")
        if len(period) != 6 or not period.isdigit():
            return False
        return 1 <= int(period[4:6]) <= 12

    @classmethod
    def _previous_calendar_period(cls, periodcode):
        if not cls._is_valid_periodcode(periodcode):
            return ""
        year = int(periodcode[:4])
        month = int(periodcode[4:6])
        if month == 1:
            return f"{year - 1:04d}12"
        return f"{year:04d}{month - 1:02d}"

    def _filter_fact_scope(self, queryset, filters):
        """Apply non-period dashboard filters to the long-format HMIS facts."""
        if filters["prov"]:
            queryset = queryset.filter(prov=filters["prov"])
        if filters["dist"]:
            queryset = queryset.filter(dist=filters["dist"])
        if filters["hf"]:
            queryset = queryset.filter(hf=filters["hf"])
        if filters["facility_group"] == "hiva":
            queryset = queryset.filter(hiva_hfs=True)
        elif filters["facility_group"] == "non_hiva":
            queryset = queryset.filter(hiva_hfs=False)
        return queryset

    def _resolve_comparison_periods(self, fact_queryset, filters):
        available_codes = [
            value
            for value in fact_queryset.exclude(periodcode="")
            .values_list("periodcode", flat=True)
            .distinct()
            .order_by("-periodcode")
            if self._is_valid_periodcode(value)
        ]
        available_set = set(available_codes)

        requested_current = ""
        current_period = ""
        current_unavailable = False

        if filters["year"] is not None and filters["month"] is not None:
            requested_current = f"{filters['year']:04d}{filters['month']:02d}"
            if requested_current in available_set:
                current_period = requested_current
            else:
                current_unavailable = True
        elif filters["year"] is not None:
            current_period = next(
                (
                    code
                    for code in available_codes
                    if code.startswith(f"{filters['year']:04d}")
                ),
                "",
            )
            current_unavailable = not bool(current_period)
        elif filters["month"] is not None:
            current_period = next(
                (
                    code
                    for code in available_codes
                    if int(code[4:6]) == filters["month"]
                ),
                "",
            )
            current_unavailable = not bool(current_period)
        elif available_codes:
            current_period = available_codes[0]

        exact_previous = self._previous_calendar_period(current_period)
        requested_comparison = filters["comparison_period"]
        comparison_period = ""
        comparison_mode = "none"

        if (
            current_period
            and requested_comparison in available_set
            and requested_comparison < current_period
        ):
            comparison_period = requested_comparison
            comparison_mode = "selected"
        elif current_period and exact_previous in available_set:
            comparison_period = exact_previous
            comparison_mode = "exact"
        elif current_period:
            comparison_period = next(
                (code for code in available_codes if code < current_period),
                "",
            )
            if comparison_period:
                comparison_mode = "fallback"

        available_periods = [
            {
                "value": code,
                "label": self._period_label(code),
                "is_current": code == current_period,
                "is_comparison": code == comparison_period,
                "can_compare": bool(current_period and code < current_period),
            }
            for code in available_codes
        ]

        if current_unavailable:
            if requested_current:
                status_message = (
                    f"No HMIS fact report is available for "
                    f"{self._period_label(requested_current)} under the active filters. "
                    "Use the Year and Month filters to choose one of the available months shown below."
                )
            else:
                status_message = (
                    "No HMIS fact report matches the selected year or month. "
                    "Use the Year and Month filters to choose one of the available months shown below."
                )
        elif not current_period:
            status_message = "No HMIS fact reporting month is available under the active filters."
        elif comparison_mode == "selected":
            status_message = (
                f"Comparing {self._period_label(current_period)} with the "
                f"manually selected month, {self._period_label(comparison_period)}."
            )
        elif comparison_mode == "exact":
            status_message = (
                f"Comparing {self._period_label(current_period)} with the "
                f"immediately preceding calendar month, "
                f"{self._period_label(comparison_period)}."
            )
        elif comparison_mode == "fallback":
            status_message = (
                f"{self._period_label(exact_previous)} is not available under the active "
                f"filters. The comparison therefore uses the closest earlier available "
                f"month, {self._period_label(comparison_period)}."
            )
        else:
            status_message = (
                f"{self._period_label(current_period)} is available, but no earlier "
                "reporting month is available for comparison."
            )

        return {
            "available_codes": available_codes,
            "available_periods": available_periods,
            "current_period": current_period,
            "current_label": self._period_label(current_period)
            if current_period
            else "Not available",
            "comparison_period": comparison_period,
            "comparison_label": self._period_label(comparison_period)
            if comparison_period
            else "Not available",
            "exact_previous_period": exact_previous,
            "comparison_mode": comparison_mode,
            "status_message": status_message,
        }

    def _indicator_period_values(self, fact_queryset, periodcode):
        if not periodcode:
            return {}
        grouped = (
            fact_queryset.filter(periodcode=periodcode)
            .values("indicator_code")
            .annotate(
                indicator_name=Max("indicator_name"),
                total=Sum("value"),
                reported_values=Count("value"),
                facility_count=Count(
                    "hf",
                    filter=Q(value__isnull=False),
                    distinct=True,
                ),
            )
        )
        return {item["indicator_code"]: item for item in grouped}

    def _indicator_metadata(self):
        metadata = {}
        rows = (
            IndicatorMetadata.objects.all()
            .order_by("-is_active", "sort_order", "indicator_name")
            .values(
                "indicator_code",
                "indicator_name",
                "indicator_short_name",
                "indicator_group",
                "indicator_domain",
                "sort_order",
                "is_active",
            )
        )
        for item in rows:
            metadata.setdefault(item["indicator_code"], item)
        return metadata

    def _monthly_indicator_comparison(self, fact_queryset, filters):
        period_data = self._resolve_comparison_periods(fact_queryset, filters)
        current_values = self._indicator_period_values(
            fact_queryset, period_data["current_period"]
        )
        comparison_values = self._indicator_period_values(
            fact_queryset, period_data["comparison_period"]
        )
        metadata = self._indicator_metadata()

        indicator_codes = set(current_values) | set(comparison_values)
        rows = []
        for code in indicator_codes:
            current = current_values.get(code)
            previous = comparison_values.get(code)
            meta = metadata.get(code, {})

            current_total = (
                self._decimal(current["total"])
                if current and current["reported_values"]
                else None
            )
            previous_total = (
                self._decimal(previous["total"])
                if previous and previous["reported_values"]
                else None
            )

            absolute_change = None
            percent_change = None
            if current_total is not None and previous_total is not None:
                absolute_change = current_total - previous_total
                if previous_total != 0:
                    percent_change = self._round2(
                        absolute_change / previous_total * Decimal("100")
                    )

            if current_total is None:
                direction = "Not reported in current month"
                direction_class = "missing"
                availability = "Previous month only"
            elif previous_total is None:
                direction = "New / no previous value"
                direction_class = "new"
                availability = "Current month only"
            elif absolute_change > 0:
                direction = "Increased"
                direction_class = "increase"
                availability = "Both months"
            elif absolute_change < 0:
                direction = "Decreased"
                direction_class = "decrease"
                availability = "Both months"
            else:
                direction = "No change"
                direction_class = "same"
                availability = "Both months"

            fact_name = ""
            if current:
                fact_name = current["indicator_name"] or ""
            elif previous:
                fact_name = previous["indicator_name"] or ""
            full_name = meta.get("indicator_name") or fact_name or code
            short_name = meta.get("indicator_short_name") or full_name
            sort_order = meta.get("sort_order")

            rows.append(
                {
                    "indicator_code": code,
                    "indicator_name": full_name,
                    "indicator_short_name": short_name,
                    "indicator_group": meta.get("indicator_group") or "Not classified",
                    "indicator_domain": meta.get("indicator_domain") or "Not classified",
                    "sort_order": sort_order,
                    "current_total": current_total,
                    "current_total_display": self._number_display(current_total),
                    "current_facilities": current["facility_count"] if current else 0,
                    "previous_total": previous_total,
                    "previous_total_display": self._number_display(previous_total),
                    "previous_facilities": previous["facility_count"] if previous else 0,
                    "absolute_change": absolute_change,
                    "absolute_change_display": self._number_display(absolute_change),
                    "percent_change": percent_change,
                    "percent_change_display": self._percent_display(percent_change),
                    "direction": direction,
                    "direction_class": direction_class,
                    "availability": availability,
                }
            )

        rows.sort(
            key=lambda row: (
                row["sort_order"] is None,
                row["sort_order"] if row["sort_order"] is not None else 0,
                row["indicator_group"].lower(),
                row["indicator_name"].lower(),
                row["indicator_code"].lower(),
            )
        )

        comparable_count = sum(
            1
            for row in rows
            if row["current_total"] is not None and row["previous_total"] is not None
        )
        increased_count = sum(1 for row in rows if row["direction_class"] == "increase")
        decreased_count = sum(1 for row in rows if row["direction_class"] == "decrease")
        unchanged_count = sum(1 for row in rows if row["direction_class"] == "same")
        current_only_count = sum(1 for row in rows if row["direction_class"] == "new")
        previous_only_count = sum(1 for row in rows if row["direction_class"] == "missing")

        chart_labels = []
        for row in rows:
            label = f"{row['indicator_short_name']} ({row['indicator_code']})"
            chart_labels.append(label if len(label) <= 100 else f"{label[:97]}...")

        period_data.update(
            {
                "rows": rows,
                "indicator_count": len(rows),
                "comparable_count": comparable_count,
                "increased_count": increased_count,
                "decreased_count": decreased_count,
                "unchanged_count": unchanged_count,
                "current_only_count": current_only_count,
                "previous_only_count": previous_only_count,
                "chart_height": max(380, min(len(rows) * 25 + 100, 12000)),
                "chart": {
                    "labels": chart_labels,
                    "current_values": [
                        float(row["current_total"])
                        if row["current_total"] is not None
                        else None
                        for row in rows
                    ],
                    "comparison_values": [
                        float(row["previous_total"])
                        if row["previous_total"] is not None
                        else None
                        for row in rows
                    ],
                },
            }
        )
        return period_data

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
            annotations[field] = Sum(field)

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
                row[field] = self._decimal(item[field])
                row[f"{field}_display"] = self._number_display(item[field])
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

    def _project_comparison(self, queryset, selected_indicator):
        rows = []
        grouped = (
            queryset.values("hiva_hfs")
            .annotate(
                reporting_records=Count("id"),
                facility_count=Count("hf", distinct=True),
                selected_total=Sum(selected_indicator),
                selected_average=Avg(selected_indicator),
            )
            .order_by("-hiva_hfs")
        )
        for item in grouped:
            rows.append(
                {
                    "label": "HIVA Health Facilities"
                    if item["hiva_hfs"]
                    else "Non-HIVA Health Facilities",
                    "reporting_records": item["reporting_records"],
                    "facility_count": item["facility_count"],
                    "total": float(self._decimal(item["selected_total"])),
                    "average": self._round2(item["selected_average"]) or 0,
                }
            )
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
        project_rows = self._project_comparison(queryset, selected_indicator)

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

        chart_data = {
            "has_data": bool(reporting_records),
            "selected_indicator": selected_label,
            "monthly": {
                "labels": [row["period"] for row in monthly_rows],
                "values": [float(row["selected_total"]) for row in monthly_rows],
            },
            "service_volume": {
                "labels": [label for _field, label in self.INDICATORS],
                "values": [float(totals[field]) for field in self.INDICATOR_FIELDS],
            },
            "province": {
                "labels": [row["province"] for row in province_rows[:15]],
                "values": [
                    float(row["selected_total"]) for row in province_rows[:15]
                ],
            },
            "facility_group": {
                "labels": [row["label"] for row in project_rows],
                "values": [row["average"] for row in project_rows],
            },
            "continuum": {
                "labels": [
                    "ANC2 / ANC1",
                    "ANC3 / ANC1",
                    "ANC4 / ANC1",
                    "PNC2 / PNC1",
                ],
                "values": [
                    self._percent(totals["anc2"], totals["anc1"]),
                    self._percent(totals["anc3"], totals["anc1"]),
                    anc4_ratio,
                    pnc2_ratio,
                ],
            },
            "delivery": {
                "labels": ["Normal", "Assisted", "C-section"],
                "values": [
                    float(totals["n_delivery"]),
                    float(totals["a_delivery"]),
                    float(totals["c_section"]),
                ],
            },
        }

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
            "project_rows": project_rows,
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

        comparison = data["monthly_indicator_comparison"]
        comparison_sheet = workbook.create_sheet("All Indicator Comparison")
        comparison_sheet.append(
            [
                "Indicator Code",
                "Indicator Name",
                "Short Name",
                "Indicator Group",
                "Indicator Domain",
                f"{comparison['comparison_label']} Total",
                f"{comparison['comparison_label']} Reporting HFs",
                f"{comparison['current_label']} Total",
                f"{comparison['current_label']} Reporting HFs",
                "Absolute Change",
                "Percent Change",
                "Direction",
                "Data Availability",
            ]
        )
        for row in comparison["rows"]:
            comparison_sheet.append(
                [
                    row["indicator_code"],
                    row["indicator_name"],
                    row["indicator_short_name"],
                    row["indicator_group"],
                    row["indicator_domain"],
                    float(row["previous_total"])
                    if row["previous_total"] is not None
                    else None,
                    row["previous_facilities"],
                    float(row["current_total"])
                    if row["current_total"] is not None
                    else None,
                    row["current_facilities"],
                    float(row["absolute_change"])
                    if row["absolute_change"] is not None
                    else None,
                    row["percent_change"],
                    row["direction"],
                    row["availability"],
                ]
            )
        self._style_worksheet(comparison_sheet)

        available_sheet = workbook.create_sheet("Available HMIS Months")
        available_sheet.append(["Period Code", "Reporting Month", "Role"])
        for period in comparison["available_periods"]:
            role = ""
            if period["is_current"]:
                role = "Current month"
            elif period["is_comparison"]:
                role = "Comparison month"
            available_sheet.append([period["value"], period["label"], role])
        self._style_worksheet(available_sheet)

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

        fact_scope = self._filter_fact_scope(HMISFact.objects.all(), filters)
        monthly_comparison = self._monthly_indicator_comparison(
            fact_scope,
            filters,
        )
        data["monthly_indicator_comparison"] = monthly_comparison
        data["chart_data"]["monthly_comparison"] = {
            "labels": monthly_comparison["chart"]["labels"],
            "current_label": monthly_comparison["current_label"],
            "current_values": monthly_comparison["chart"]["current_values"],
            "comparison_label": monthly_comparison["comparison_label"],
            "comparison_values": monthly_comparison["chart"]["comparison_values"],
            "has_current": bool(monthly_comparison["current_period"]),
            "has_comparison": bool(monthly_comparison["comparison_period"]),
        }

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
            "comparison_period",
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
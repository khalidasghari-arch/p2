from django.contrib import admin
from .models import Indicator, IndicatorReport

@admin.register(Indicator)
class IndicatorAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "area", "level","category", "definition", "data_source", "frequency", "baseline", "target")
    list_filter = ("level", "frequency")
    search_fields = ("code", "name")


@admin.register(IndicatorReport)
class IndicatorReportAdmin(admin.ModelAdmin):
    list_display = ("indicator", "year", "month", "quarter", "facility", "value")
    list_filter = ("year", "quarter", "indicator", "province")
    search_fields = ("indicator__name",)
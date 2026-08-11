from django.db import models

class Indicator(models.Model):

    INDICATOR_LEVEL_CHOICES = [
        ("impact", "Impact"),
        ("outcome", "Outcome"),
        ("output", "Output"),
    ]

    FREQUENCY_CHOICES = [
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("annual", "Annual"),
    ]

    category = models.CharField(max_length=100, blank=True)
    sex = models.CharField(max_length=10, blank=True, null=True)
    age_group = models.CharField(max_length=50, blank=True, null=True)
    code = models.CharField(max_length=20, unique=True)  # i.1, i.2, etc
    area = models.TextField(blank=True, null=True, verbose_name="Thematic Area")
    name = models.TextField(verbose_name="Indicator")
    definition = models.TextField(blank=True, null=True)
    level = models.CharField(max_length=20, choices=INDICATOR_LEVEL_CHOICES)
    data_source = models.CharField(max_length=255, blank=True, null=True)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    baseline = models.FloatField(blank=True, null=True)
    target = models.FloatField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "PERFORMANCE INDICATOR"
        verbose_name_plural = "PERFORMANCE INDICATOR"

    def __str__(self):
        return f"{self.code} - {self.name}"# Create your models here.

class IndicatorReport(models.Model):

    REPORTING_TYPE = [
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("annual", "Annual"),
    ]

    MONTH_CHOICES = [
        (1, "Jan"), (2, "Feb"), (3, "Mar"),
        (4, "Apr"), (5, "May"), (6, "Jun"),
        (7, "Jul"), (8, "Aug"), (9, "Sep"),
        (10, "Oct"), (11, "Nov"), (12, "Dec"),
    ]

    QUARTER_CHOICES = [
        (1, "Q1"),
        (2, "Q2"),
        (3, "Q3"),
        (4, "Q4"),
    ]

    indicator = models.ForeignKey("Indicator", on_delete=models.CASCADE)
    reporting_type = models.CharField(max_length=20, choices=REPORTING_TYPE)
    year = models.IntegerField()
    month = models.IntegerField(choices=MONTH_CHOICES, blank=True, null=True)
    quarter = models.IntegerField(choices=QUARTER_CHOICES, blank=True, null=True)

    # 🔥 Your MNH hierarchy (IMPORTANT)
    province = models.ForeignKey("hiva.Province", on_delete=models.CASCADE, null=True, blank=True)
    district = models.ForeignKey("hiva.District", on_delete=models.CASCADE, null=True, blank=True)
    facility = models.ForeignKey("hiva.Facility", on_delete=models.CASCADE, null=True, blank=True)

    # Data values
    value = models.FloatField()
    numerator = models.FloatField(blank=True, null=True)
    denominator = models.FloatField(blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "INDICATOR TRACKING"
        verbose_name_plural = "INDICATOR TRACKING"
        unique_together = (
            "indicator",
            "year",
            "month",
            "quarter",
            "facility",
        )

    def __str__(self):
        return f"{self.indicator.code} - {self.year}"
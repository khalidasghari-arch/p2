from django.db import models
from django.conf import settings

class HMISRawUpload(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("VALIDATED", "Validated"),
        ("IMPORTED", "Imported"),
        ("FAILED", "Failed"),
    ]

    title = models.CharField(max_length=255, blank=True, default="", verbose_name="Spread sheet Name")
    file = models.FileField(upload_to="hmis/raw/", verbose_name="File Path")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    report = models.JSONField(default=dict, blank=True)

    row_count = models.IntegerField(default=0, verbose_name="Rows Count")
    hf_count = models.IntegerField(default=0, verbose_name="Health Facility Count")
    period_min = models.CharField(max_length=6, blank=True, default="", verbose_name="Start Month")  # YYYYMM
    period_max = models.CharField(max_length=6, blank=True, default="", verbose_name="End Month")  # YYYYMM

    class Meta:
        verbose_name = "FACILITY DATA DUMP"
        verbose_name_plural = "FACILITY DATA DUMP"

    def __str__(self):
        return f"HMIS Upload #{self.id} - {self.status}"

class HMISFact(models.Model):
    """
    Long-format fact table:
    One row per facility + period + indicator.
    """
    source_upload = models.ForeignKey(HMISRawUpload, on_delete=models.PROTECT, related_name="facts")

    prov = models.CharField(max_length=255, blank=True, default="", verbose_name="Province")
    dist = models.CharField(max_length=255, blank=True, default="", verbose_name="District")
    hf = models.CharField(max_length=255, db_index=True, verbose_name="Health Facility")

    periodcode = models.CharField(max_length=6, db_index=True)  # YYYYMM
    year = models.IntegerField(db_index=True)
    month = models.IntegerField(db_index=True)
    month_name = models.CharField(max_length=20, blank=True, default="")

    hf_name_cleaned = models.CharField(max_length=255, blank=True, default="")
    hfid = models.IntegerField(default=0, db_index=True)
    hiva_hfs = models.BooleanField(default=False, db_index=True, verbose_name="HIVA HF")

    indicator_code = models.CharField(max_length=128, db_index=True)
    indicator_name = models.CharField(max_length=512)
    value = models.DecimalField(max_digits=18, decimal_places=0, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "FACILITY REPORT"
        verbose_name_plural = "FACILITY REPORT"

        constraints = [
            models.UniqueConstraint(
                fields=["hf", "periodcode", "indicator_code"],
                name="uniq_hmis_hf_period_indicator",
            )
        ]

    def __str__(self):
        return f"{self.hf} {self.periodcode} {self.indicator_code}={self.value}"
    
class HMISMonthlySummary(models.Model):
    source_upload = models.ForeignKey(HMISRawUpload, on_delete=models.PROTECT, related_name="summaries")

    prov = models.CharField(max_length=255, blank=True, default="")
    dist = models.CharField(max_length=255, blank=True, default="")
    hf = models.CharField(max_length=255, db_index=True)

    periodcode = models.CharField(max_length=6, db_index=True)  # YYYYMM
    year = models.IntegerField(db_index=True)
    month = models.IntegerField(db_index=True)
    month_name = models.CharField(max_length=20, blank=True, default="")

    hfid = models.IntegerField(default=0, db_index=True)
    hiva_hfs = models.BooleanField(default=False, db_index=True)

    # Compare-friendly columns (add more anytime)
    anc1 = models.DecimalField(max_digits=18, decimal_places=0, null=True, blank=True)
    anc2 = models.DecimalField(max_digits=18, decimal_places=0, null=True, blank=True)
    anc3 = models.DecimalField(max_digits=18, decimal_places=0, null=True, blank=True)
    anc4 = models.DecimalField(max_digits=18, decimal_places=0, null=True, blank=True)
    
    pnc1 = models.DecimalField(max_digits=18, decimal_places=0, null=True, blank=True)
    pnc2 = models.DecimalField(max_digits=18, decimal_places=0, null=True, blank=True)

    n_delivery = models.DecimalField(max_digits=18, decimal_places=0, null=True, blank=True)
    a_delivery = models.DecimalField(max_digits=18, decimal_places=0, null=True, blank=True)
    c_section = models.DecimalField(max_digits=18, decimal_places=0, null=True, blank=True)

    lbw = models.DecimalField(max_digits=18, decimal_places=0, null=True, blank=True)
    stillbirth = models.DecimalField(max_digits=18, decimal_places=0, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "FACILITY MONTHLY SUMMARY"
        verbose_name_plural = "FACILITY MONTHLY SUMMARY"

        constraints = [
            models.UniqueConstraint(fields=["hf", "periodcode"], name="uniq_hmis_summary_hf_period")
        ]

    def __str__(self):
        return f"{self.hf} {self.periodcode}"
    
class IndicatorMetadata(models.Model):
    indicator_code = models.CharField(max_length=100)
    indicator_name = models.CharField(max_length=255)
    indicator_short_name = models.CharField(max_length=255, blank=True, null=True)
    indicator_group = models.CharField(max_length=100, blank=True, null=True)
    indicator_domain = models.CharField(max_length=100, blank=True, null=True)
    indicator_description = models.TextField(blank=True, null=True)
    numerator_definition = models.TextField(blank=True, null=True)
    denominator_definition = models.TextField(blank=True, null=True)
    unit_of_measure = models.CharField(max_length=50, blank=True, null=True)
    reporting_level = models.CharField(max_length=100, blank=True, null=True)
    data_source = models.CharField(max_length=50, default="HMIS")
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name ="INDICATOR METADATA"
        verbose_name_plural = "INDICATOR METADATA"
        db_table = "hmis_indicator_metadata"
        unique_together = ("indicator_code", "indicator_name")
        ordering = ["sort_order", "indicator_name"]

    def __str__(self):
        return f"{self.indicator_name} ({self.indicator_code})"
    
class HMISDashboard(HMISMonthlySummary):
    class Meta:
        proxy = True
        verbose_name = "HMIS DASHBOARD"
        verbose_name_plural = "HMIS DASHBOARD"


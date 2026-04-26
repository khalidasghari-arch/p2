from django.db import models


class QQMUpload(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("done", "Done"),
        ("failed", "Failed"),
    ]

    title = models.CharField(max_length=255)
    round_name = models.CharField(max_length=50, help_text="Example: R1, R2, R3, R4")
    excel_file = models.FileField(upload_to="qqm_uploads/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    processed = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    error_message = models.TextField(blank=True, null=True)

    total_imported = models.PositiveIntegerField(default=0)
    total_matched_facilities = models.PositiveIntegerField(default=0)
    total_unmatched_facilities = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.title} - {self.round_name}"


class QQMFacilityScore(models.Model):
    upload = models.ForeignKey(
        QQMUpload,
        on_delete=models.CASCADE,
        related_name="facility_scores",
    )

    facility = models.ForeignKey(
        "hiva.Facility",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="qqm_scores",
    )

    hfcode = models.IntegerField(db_index=True)
    hfname_excel = models.CharField(max_length=255, blank=True, null=True)

    structural_score = models.FloatField(blank=True, null=True)
    outcome_score = models.FloatField(blank=True, null=True)
    content_score = models.FloatField(blank=True, null=True)
    qqm_score = models.FloatField(blank=True, null=True)

    class Meta:
        unique_together = ("upload", "hfcode")
        ordering = ["upload", "hfcode"]

    def __str__(self):
        return f"{self.hfcode} - {self.upload.round_name}"


class QQMRawData(models.Model):
    score = models.OneToOneField(
        QQMFacilityScore,
        on_delete=models.CASCADE,
        related_name="raw_data",
    )

    structural_data = models.JSONField(blank=True, null=True)
    exit_vignette_data = models.JSONField(blank=True, null=True)
    workforce_data = models.JSONField(blank=True, null=True)
    mss_data = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"Raw data for {self.score}"
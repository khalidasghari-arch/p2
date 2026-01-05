from django.db import models
from django.conf import settings
from django.utils import timezone

# If you already have these in your project, import them instead.
# from hiva.models import Province, District, Facility

THEME_CHOICES = (
    ("ANC", "ANC"),
    ("PNC", "PNC"),
    ("L&D", "Labour & Delivery"),
    ("PPH", "PPH"),
    ("PEE", "PE/E"),
    ("MNM", "Maternal Near Miss"),
    ("NBCC", "NBCC / Newborn"),
    ("QoC", "Quality of Care"),
    ("Other", "Other"),
)

DOC_TYPE_CHOICES = (
    ("brief", "Learning Brief"),
    ("sop", "SOP / Guideline"),
    ("case", "Case Study"),
    ("aar", "After Action Review"),
    ("report", "Report"),
    ("training", "Training Material"),
)

ACTION_STATUS = (
    ("pending", "Pending"),
    ("in_progress", "In progress"),
    ("done", "Done"),
    ("blocked", "Blocked"),
)

class KMDocument(models.Model):
    """
    Knowledge products: learning briefs, SOPs, AARs, case studies, etc.
    """
    title = models.CharField(max_length=255, verbose_name="Name of the knowledge product")
    doc_type = models.CharField(max_length=20, choices=DOC_TYPE_CHOICES, verbose_name="Type of document")
    theme = models.CharField(max_length=20, choices=THEME_CHOICES, default="ANC", verbose_name="Technical Area")

    # Link to geography / facility
    province = models.ForeignKey("hiva.Province", on_delete=models.PROTECT, null=True, blank=True, verbose_name="Province")
    district = models.ForeignKey("hiva.District", on_delete=models.PROTECT, null=True, blank=True, verbose_name="District")
    facility = models.ForeignKey("hiva.Facility", on_delete=models.PROTECT, null=True, blank=True, verbose_name="Health Facility")

    # Time period (monthly tracking)
    year = models.PositiveIntegerField(verbose_name="Year")
    month = models.PositiveIntegerField(verbose_name="Month")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        related_name="km_docs_created", 
        editable=False)
    created_at = models.DateTimeField(
        default=timezone.now, editable=False)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="km_docs_updated",
        editable=False,
        null=True,
        blank=True)
    updated_at = models.DateTimeField(
        auto_now=True, 
        editable=False)

    file = models.FileField(
        upload_to="km_docs/", 
        null=True, 
        blank=True, 
        verbose_name="File")  # optional
    notes = models.TextField(
        blank=True, 
        default="", 
        verbose_name="Notes")

    class Meta:
        verbose_name = "Knowledge MGT Documents"
        verbose_name_plural = "Knowledge MGT Documents"
        ordering = ["-year", "-month", "-created_at"]

    def __str__(self):
        return f"{self.title} ({self.year}-{self.month:02d})"

class KMRecommendation(models.Model):
    """
    Recommendations coming from mentorship/supervision/QI.
    """
    theme = models.CharField(
        max_length=20, 
        choices=THEME_CHOICES, 
        default="ANC", verbose_name="Technical Area of Recommendation")
    
    province = models.ForeignKey(
        "hiva.Province", 
        on_delete=models.PROTECT,
        verbose_name="Province")
    district = models.ForeignKey(
        "hiva.District", 
        on_delete=models.PROTECT, 
        null=True, blank=True, verbose_name="District")
    facility = models.ForeignKey(
        "hiva.Facility", 
        on_delete=models.PROTECT, verbose_name="Health Facility")

    # Link to document or mentorship visit if you have that model
    source_document = models.ForeignKey(
        KMDocument, on_delete=models.SET_NULL, 
        null=True, blank=True, verbose_name="Source Document")

    recommendation = models.TextField(verbose_name="Recommandation")
    responsible_person = models.CharField(
        max_length=255, 
        blank=True, default="", verbose_name="Responsible Person")

    year = models.PositiveIntegerField(verbose_name="Year")
    month = models.PositiveIntegerField(verbose_name="Month")

    status = models.CharField(
        max_length=20, 
        choices=ACTION_STATUS, 
        default="pending", verbose_name="Action Progress")
    due_date = models.DateField(
        null=True, blank=True,
        verbose_name="Deadline")

    implemented_on = models.DateField(
        null=True, blank=True, verbose_name="Date Completed")
    evidence_notes = models.TextField(
        blank=True, default="", verbose_name="Evidence that Action Happened")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        related_name="km_recs_created",
        editable=False)
    
    created_at = models.DateTimeField(
        default=timezone.now, editable=False)
    
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="km_recs_updated",
        editable=False,
        null=True,
        blank=True)
    
    updated_at = models.DateTimeField(
        auto_now=True, 
        editable=False)

    class Meta:
        verbose_name = "Knowledge MGT Recommandations"
        verbose_name_plural = "Knowledge MGT Recommandations"
        ordering = ["-year", "-month", "-created_at"]

    def __str__(self):
        return f"{self.facility} - {self.theme} - {self.status}"

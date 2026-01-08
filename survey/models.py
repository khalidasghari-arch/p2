from django.db import models
from django.conf import settings

class PatientSafetyHeader(models.Model):
    ENGLISH_MONTH_CHOICES = [
        ("1", "January"), ("2", "February"), ("3", "March"), ("4", "April"),
        ("5", "May"), ("6", "June"), ("7", "July"), ("8", "August"),
        ("9", "September"), ("10", "October"), ("11", "November"), ("12", "December"),
    ]
    YEAR_CHOICES = [("2025", "2025"), ("2026", "2026"), ("2027", "2027")]

    surveymonth = models.CharField(max_length=2, choices=ENGLISH_MONTH_CHOICES)
    surveyyear = models.CharField(max_length=4, choices=YEAR_CHOICES)
    key_intervention_name = models.CharField(max_length=255, null=True, blank=True)

    facility = models.ForeignKey("hiva.Facility", on_delete=models.PROTECT, related_name="patientsafety_headers")
    assessor = models.ForeignKey("hiva.Assessor", on_delete=models.PROTECT, related_name="patientsafety_assessments")
    staff_profession = models.ForeignKey(
        'hiva.Position',
        on_delete=models.PROTECT,   # or your existing on_delete
        null=True,
        blank=True,
        related_name='patient_safety_headers')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    STATUS = (
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )

    status = models.CharField(max_length=20, choices=STATUS, default="draft")
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True, related_name="ps_submitted"
    )
    submitted_at = models.DateTimeField(null=True, blank=True)

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True, related_name="ps_approved"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approval_note = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "Patient Safety Culture"
        verbose_name_plural = "Patient Safety Culture"

    def __str__(self):
        return f"{self.facility} | {self.surveymonth}-{self.surveyyear}"

class WorkArea(models.Model):
    work_area_name = models.CharField(max_length=150)

    class Meta:
        verbose_name = "Work Area"
        verbose_name_plural = "Work Areas"

    def __str__(self):
        return self.work_area_name


class PatientSafetyDetails(models.Model):
    header = models.OneToOneField(
        PatientSafetyHeader,
        on_delete=models.PROTECT,
        related_name="details"
    )

    work_area = models.ForeignKey(
        WorkArea,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="patientsafety_details"
    )

    LIKERT_1_5 = [
        (1, "Strongly Disagree"),
        (2, "Disagree"),
        (3, "Neither Agree nor Disagree"),
        (4, "Agree"),
        (5, "Strongly Agree"),
        (9, "Does Not Apply / Don't Know"),
    ]

    COMM_CHOICES = [
        (1, "Never"),
        (2, "Rarely"),
        (3, "Sometimes"),
        (4, "Most of the time"),
        (5, "Always"),
        (9, "Does Not Apply / Don't Know"),
    ]

    COMM_COUNT = [
        (1, "None"),
        (2, "1 to 2"),
        (3, "3 to 5"),
        (4, "6 to 10"),
        (5, "11 or more"),
    ]

    RATING = [
        (1, "Poor"),
        (2, "Fair"),
        (3, "Good"),
        (4, "Very Good"),
        (5, "Excellent"),
    ]

    YEARS_HOSP = [
        ("1", "Less than 1 year"),
        ("2", "1 to 5 years"),
        ("3", "6 to 10 years"),
        ("4", "11 or more years"),
    ]
    HOURS_WEEK = [
        ("1", "Less than 30 hours per week"),
        ("2", "30 to 40 hours per week"),
        ("3", "More than 40 hours per week"),
    ]
    PATIENT_CONTACT = [
        ("1", "YES, I typically have direct interaction or contact with patients"),
        ("2", "NO, I typically do NOT have direct interaction or contact with patients"),
    ]

    # A1–A14
    a1 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True)
    a2 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True)
    a3 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True)
    a4 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True)
    a5 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True)
    a6 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True)
    a7 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True)
    a8 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True)
    a9 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True)
    a10 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True)
    a11 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True)
    a12 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True)
    a13 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True)
    a14 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True)

    # B1–B3
    b1 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True)
    b2 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True)
    b3 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True)

    # C1–C7
    c1 = models.PositiveSmallIntegerField(choices=COMM_CHOICES, null=True, blank=True)
    c2 = models.PositiveSmallIntegerField(choices=COMM_CHOICES, null=True, blank=True)
    c3 = models.PositiveSmallIntegerField(choices=COMM_CHOICES, null=True, blank=True)
    c4 = models.PositiveSmallIntegerField(choices=COMM_CHOICES, null=True, blank=True)
    c5 = models.PositiveSmallIntegerField(choices=COMM_CHOICES, null=True, blank=True)
    c6 = models.PositiveSmallIntegerField(choices=COMM_CHOICES, null=True, blank=True)
    c7 = models.PositiveSmallIntegerField(choices=COMM_CHOICES, null=True, blank=True)

    # D1–D3
    d1 = models.PositiveSmallIntegerField(choices=COMM_CHOICES, null=True, blank=True)
    d2 = models.PositiveSmallIntegerField(choices=COMM_CHOICES, null=True, blank=True)
    d3 = models.PositiveSmallIntegerField(choices=COMM_COUNT, null=True, blank=True)

    # E1
    e1 = models.PositiveSmallIntegerField(choices=RATING, null=True, blank=True)

    # F1–F6
    f1 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True)
    f2 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True)
    f3 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True)
    f4 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True)
    f5 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True)
    f6 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True)

    # G1–G4
    g1 = models.CharField(max_length=1, choices=YEARS_HOSP, null=True, blank=True)
    g2 = models.CharField(max_length=1, choices=YEARS_HOSP, null=True, blank=True)
    g3 = models.CharField(max_length=1, choices=HOURS_WEEK, null=True, blank=True)
    g4 = models.CharField(max_length=1, choices=PATIENT_CONTACT, null=True, blank=True)

    comment = models.TextField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="patientsafety_details_created",
        null=True, blank=True
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="patientsafety_details_updated",
        null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Patient Safety Survey Details"
        verbose_name_plural = "Patient Safety Survey Details"

    def __str__(self):
        return f"Details for {self.header}"

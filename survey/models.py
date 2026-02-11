from django.db import models
from django.conf import settings

class PatientSafetyHeader(models.Model):
    ENGLISH_MONTH_CHOICES = [
        ("1", "January"), ("2", "February"), ("3", "March"), ("4", "April"),
        ("5", "May"), ("6", "June"), ("7", "July"), ("8", "August"),
        ("9", "September"), ("10", "October"), ("11", "November"), ("12", "December"),
    ]
    YEAR_CHOICES = [("2025", "2025"), ("2026", "2026"), ("2027", "2027")]
    KEY_INTERVENTION_CHOICES = [("AIM", "AIM"),("SAFE_SURGERY", "SAFE_SURGERY")]

    surveymonth = models.CharField(max_length=2, choices=ENGLISH_MONTH_CHOICES)
    surveyyear = models.CharField(max_length=4, choices=YEAR_CHOICES)
    key_intervention_name = models.CharField(max_length=255, default="AIM", choices=KEY_INTERVENTION_CHOICES)

    facility = models.ForeignKey("hiva.Facility", on_delete=models.PROTECT, related_name="patientsafety_headers")
    assessor = models.ForeignKey("hiva.Assessor", on_delete=models.PROTECT, related_name="patientsafety_assessments")
    staff_profession = models.ForeignKey(
        "hiva.Position",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="patient_safety_headers",
    )

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
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ps_submitted",
    )
    submitted_at = models.DateTimeField(null=True, blank=True)

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ps_approved",
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
    a1 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True, verbose_name="1.In this unit, we work together as an effective team")
    a2 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True, verbose_name="2.In this unit, we have enough staff to handle the workload")
    a3 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True, verbose_name="3.Staff in this unit work longer hours than is best for patient care")
    a4 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True, verbose_name="4.This unit regularly reviews work processes to determine if changes are needed to improve patient safety")
    a5 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True, verbose_name="5.This unit relies too much on temporary, float, or PRN staff")
    a6 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True, verbose_name="6.In this unit, staff feel like their mistakes are held against them")
    a7 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True, verbose_name="7.When an event is reported in this unit, it feels like the person is being written up, not the problem")
    a8 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True, verbose_name="8.During busy times, staff in this unit help each other")
    a9 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True, verbose_name="9.There is a problem with disrespectful behavior by those working in this unit")
    a10 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True, verbose_name="10.	When staff make errors, this unit focuses on learning rather than blaming individuals")
    a11 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True, verbose_name="11.The work pace in this unit is so rushed that it negatively affects patient safety")
    a12 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True, verbose_name="12.In this unit, changes to improve patient safety are evaluated to see how well they worked")
    a13 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True, verbose_name="13.In this unit, there is a lack of support for staff involved in patient safety errors ")
    a14 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True, verbose_name="14.This unit lets the same patient safety problems keep happening ")

    # B1–B3
    b1 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True, verbose_name="1.My supervisor, manager, or clinical leader seriously considers staff suggestions for improving patient safety")
    b2 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True, verbose_name="2.My supervisor, manager, or clinical leader wants us to work faster during busy times, even if it means taking shortcuts")
    b3 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True, verbose_name="3.My supervisor, manager, or clinical leader takes action to address patient safety concerns that are brought to their attention")

    # C1–C7
    c1 = models.PositiveSmallIntegerField(choices=COMM_CHOICES, null=True, blank=True, verbose_name="1.We are informed about errors that happen in this unit ")
    c2 = models.PositiveSmallIntegerField(choices=COMM_CHOICES, null=True, blank=True, verbose_name="2.When errors happen in this unit, we discuss ways to prevent them from happening again")
    c3 = models.PositiveSmallIntegerField(choices=COMM_CHOICES, null=True, blank=True, verbose_name="3.In this unit, we are informed about changes that are made based on event reports")
    c4 = models.PositiveSmallIntegerField(choices=COMM_CHOICES, null=True, blank=True, verbose_name="4.In this unit, staff speak up if they see something that may negatively affect patient care")
    c5 = models.PositiveSmallIntegerField(choices=COMM_CHOICES, null=True, blank=True, verbose_name="5.When staff in this unit see someone with more authority doing something unsafe for patients, they speak up")
    c6 = models.PositiveSmallIntegerField(choices=COMM_CHOICES, null=True, blank=True, verbose_name="6.When staff in this unit speak up, those with more authority are open to their patient safety concerns")
    c7 = models.PositiveSmallIntegerField(choices=COMM_CHOICES, null=True, blank=True, verbose_name="7.In this unit, staff are afraid to ask questions when something does not seem right")

    # D1–D3
    d1 = models.PositiveSmallIntegerField(choices=COMM_CHOICES, null=True, blank=True, verbose_name="1.When a mistake is caught and corrected before reaching the patient, how often is this reported?")
    d2 = models.PositiveSmallIntegerField(choices=COMM_CHOICES, null=True, blank=True, verbose_name="2.When a mistake reaches the patient and could have harmed the patient, but did not, how often is this reported?")
    d3 = models.PositiveSmallIntegerField(choices=COMM_COUNT, null=True, blank=True, verbose_name="3.In the past 12 months, how many patient safety events have you reported?")

    # E1
    e1 = models.PositiveSmallIntegerField(choices=RATING, null=True, blank=True, verbose_name="1.How would you rate your unit/work area on patient safety?")

    # F1–F6
    f1 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True, verbose_name="1.The actions of hospital management show that patient safety is a top priority")
    f2 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True, verbose_name="2.Hospital management provides adequate resources to improve patient safety")
    f3 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True, verbose_name="3.Hospital management seems interested in patient safety only after an adverse event happens")
    f4 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True, verbose_name="4.When transferring patients from one unit to another, important information is often left out")
    f5 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True, verbose_name="5.During shift changes, important patient care information is often left out")
    f6 = models.PositiveSmallIntegerField(choices=LIKERT_1_5, null=True, blank=True, verbose_name="6.During shift changes, there is adequate time to exchange all key patient care information")

    # ============================================================
    # NEW SECTION (after F): Medication & Surgical Errors + RMC
    # (Added only — no changes to your existing fields)
    # ============================================================

    EVENT_FREQ_1_5 = [
        (1, "Never"),
        (2, "Once or twice per year"),
        (3, "Once every three months"),
        (4, "Once every month"),
        (5, "At least every 1-2 weeks"),
        (9, "Does Not Apply / Don't Know"),
    ]

    RMC_FREQ_1_5 = [
        (1, "Never"),
        (2, "Rarely"),
        (3, "Some of the time"),
        (4, "Most of the time"),
        (5, "Every time"),
        (9, "Does Not Apply / Don't Know"),
    ]

    # H1–H4: patient safety events witnessed (past 12 months)
    h1_wrong_medication = models.PositiveSmallIntegerField(
        choices=EVENT_FREQ_1_5, null=True, blank=True,
        verbose_name="H1. Wrong medication (past 12 months - frequency witnessed)"
    )
    h2_wrong_dose = models.PositiveSmallIntegerField(
        choices=EVENT_FREQ_1_5, null=True, blank=True,
        verbose_name="H2. Wrong dose of medication (past 12 months - frequency witnessed)"
    )
    h3_wrong_route = models.PositiveSmallIntegerField(
        choices=EVENT_FREQ_1_5, null=True, blank=True,
        verbose_name="H3. Wrong route of medication (past 12 months - frequency witnessed)"
    )
    h4_wrong_surgical_procedure = models.PositiveSmallIntegerField(
        choices=EVENT_FREQ_1_5, null=True, blank=True,
        verbose_name="H4. Wrong surgical procedure (past 12 months - frequency witnessed)"
    )

    # H5–H9: RMC violations witnessed (past 12 months)
    h5_physical_abuse_ld = models.PositiveSmallIntegerField(
        choices=EVENT_FREQ_1_5, null=True, blank=True,
        verbose_name="H5. Physical abuse during labor & delivery (violations witnessed)"
    )
    h6_verbal_abuse_ld = models.PositiveSmallIntegerField(
        choices=EVENT_FREQ_1_5, null=True, blank=True,
        verbose_name="H6. Verbal abuse during labor & delivery (violations witnessed)"
    )
    h7_stigma_discrimination = models.PositiveSmallIntegerField(
        choices=EVENT_FREQ_1_5, null=True, blank=True,
        verbose_name="H7. Stigma or discrimination (violations witnessed)"
    )
    h8_privacy_confidentiality = models.PositiveSmallIntegerField(
        choices=EVENT_FREQ_1_5, null=True, blank=True,
        verbose_name="H8. Violations of privacy or confidentiality (violations witnessed)"
    )
    h9_no_staff_at_birth = models.PositiveSmallIntegerField(
        choices=EVENT_FREQ_1_5, null=True, blank=True,
        verbose_name="H9. No staff member present at the time of birth (violations witnessed)"
    )

    # H10–H12: Respectful maternity care practice frequency
    h10_informed_consent = models.PositiveSmallIntegerField(
        choices=RMC_FREQ_1_5, null=True, blank=True,
        verbose_name="H10. Informed consent obtained prior to procedures/exams (labor & delivery)"
    )
    h11_companionship_choice = models.PositiveSmallIntegerField(
        choices=RMC_FREQ_1_5, null=True, blank=True,
        verbose_name="H11. Women allowed choice of companionship during labor & delivery"
    )
    h12_treated_respectfully = models.PositiveSmallIntegerField(
        choices=RMC_FREQ_1_5, null=True, blank=True,
        verbose_name="H12. Women treated with respect and in a friendly manner during labor & delivery"
    )

    # G1–G4
    g1 = models.CharField(max_length=1, choices=YEARS_HOSP, null=True, blank=True, verbose_name="How long have you worked in this hospital?")
    g2 = models.CharField(max_length=1, choices=YEARS_HOSP, null=True, blank=True, verbose_name="In this hospital, how long have you worked in your current unit/work area?")
    g3 = models.CharField(max_length=1, choices=HOURS_WEEK, null=True, blank=True, verbose_name="Typically, how many hours per week do you work in this hospital?")
    g4 = models.CharField(max_length=1, choices=PATIENT_CONTACT, null=True, blank=True, verbose_name="In your staff position, do you typically have direct interaction or contact with patients?")

    comment = models.TextField(null=True, blank=True, verbose_name="Please feel free to provide any comments about how things are done or could be done in your hospital that might affect patient safety.")

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

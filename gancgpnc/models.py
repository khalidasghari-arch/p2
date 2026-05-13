from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

class Gancohort(models.Model):
    STATUS_CHOICES = [
    ("NOT_STARTED", "Not started"),
    ("IN_PROGRESS", "In progress"),
    ("COMPLETED", "Completed"),]
     
    facility = models.ForeignKey("hiva.Facility", on_delete=models.CASCADE, verbose_name="Health Facility Name")
    cohortname = models.CharField(max_length=255, unique=True, verbose_name="Cohort Name")
    cohortnumber = models.PositiveIntegerField(default=1, verbose_name="Cohort Number")
    cohortstatus = models.CharField(max_length=20, choices=STATUS_CHOICES, default="NOT_STARTED", verbose_name="Cohort Status")
    cohortchecklist = models.CharField(max_length=255,default="G-ANC/PNC Logbook V1", verbose_name="Cohort Checklist")
    target_size = models.PositiveIntegerField(null=True, blank=True, verbose_name="Cohort Target Size")
    created_by = models.ForeignKey(
    settings.AUTH_USER_MODEL, 
    on_delete=models.PROTECT,
    related_name='gancgpnc_created_cohorts',
    editable=False, null=True, blank=True)
    created_at = models.DateTimeField(
    default=timezone.now, editable=False)
    updated_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.PROTECT,
    related_name='gancgpnc_updated_cohorts',
    editable=False,
    null=True,
    blank=True)
    updated_at = models.DateTimeField(
        auto_now=True, 
        editable=False)
    remarks = models.TextField(blank=True, null=True)

    def clean(self):
        super().clean()

    class Meta:
        verbose_name = "COHORT"
        verbose_name_plural = "COHORT"

    def __str__(self):
        return self.cohortname
    
class Gancenrollment(models.Model):
    cohortname = models.ForeignKey(Gancohort, on_delete=models.CASCADE, verbose_name="Cohort Name")
    enrollmentid= models.IntegerField(blank=True, null=True, verbose_name="Register Number")
    name = models.CharField(max_length=255, verbose_name="Name")
    fathername = models.CharField(max_length=255, verbose_name="Father Name")
    contactnumber = models.CharField(max_length=255, verbose_name="Contact Number")
    address = models.CharField(max_length=255, verbose_name="Address")
    education_level = models.CharField(max_length=255, verbose_name="Education Level", blank=True, null=True)
    gravida = models.PositiveIntegerField(verbose_name="Gravida", blank=True, null=True)
    gafirstanc = models.PositiveIntegerField(verbose_name="G-Age",
        validators=[
            MinValueValidator(20),
            MaxValueValidator(24)
        ])
    edd = models.DateField(verbose_name="Expected Date of Delivery")
    age_years = models.PositiveIntegerField(verbose_name="Age (Year)", blank=True, null=True)
    transfer_in = models.BooleanField(default=True, verbose_name="Transfer In", blank=True, null=True)
    numerof_ancvisits = models.PositiveSmallIntegerField(default=0, blank=True, null=True,verbose_name="Individual-ANC-Visits")
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "ENROLLMENT"
        verbose_name_plural = "ENROLLMENT"

    def __str__(self):
        return self.name
    
class Gancfirstsession(models.Model):
    SESSION_TYPE = [
    ("GROUP-ANC", "GROUP-ANC"),]

    SESSION_ROUND = [
    ("FIRST-SESSION", "FIRST-SESSION"),]

    INDIVIDUAL_ATTENDANCE = [
    ("GROUP", "GROUP"),
    ("INDIVIDUAL","INDIVIDUAL"),
    ("ABSENT","ABSENT"),]

    URIN_EXAM = [
    ("NO/+", "NO/+"),
    ("++","++"),
    ("+++","+++"),]

    registerid = models.ForeignKey(Gancenrollment, on_delete=models.CASCADE, verbose_name="Register Name")
    sessiontype = models.CharField(max_length=225,choices=SESSION_TYPE, default="GROUP-ANC", verbose_name="Session-Type")
    sessionround = models.CharField(max_length=255, choices=SESSION_ROUND, default="FIRST-SESSION", verbose_name="Session-Round")
    sessiondate = models.DateField()
    attendance = models.CharField(max_length=255, choices=INDIVIDUAL_ATTENDANCE, default="GROUP",verbose_name="Attendance (Group/Individual/Absent)")
    presentga = models.PositiveIntegerField(verbose_name="Present_GA")
    bp = models.CharField(max_length=255)
    dhypertension = models.BooleanField(verbose_name="Diagnosed with hypertension (Y/N)")
    rhypertensiontoMD = models.BooleanField(verbose_name="Referred  hypertension to MD (Y/N)")
    weight = models.PositiveIntegerField(verbose_name="Weight")
    anemia = models.BooleanField(verbose_name="Anemia (Y/N)")
    ironfolate = models.BooleanField(verbose_name="Iron Folate/routine Dose(Y/N)")
    ironfolatepluswomen = models.BooleanField(verbose_name="Iron folate (30+) for anemic woman(Y/N)")
    pcalcium = models.BooleanField(verbose_name="Prescribe-Calcium(Y/N)")
    acalcium = models.BooleanField(verbose_name="absorbed calcium in the last month(Y/N)")
    muac = models.DecimalField(max_digits=4, decimal_places=1,verbose_name="MUAC")
    dmam = models.BooleanField(verbose_name="Diagnosed with MAM (Y/N)")
    rmam = models.BooleanField(verbose_name="Refer MAM to Nutrition Counsellor (Y/N))")
    dsam = models.BooleanField(verbose_name="Diagnosed with SAM (Y/N)")
    rsam = models.BooleanField(verbose_name="Refer SAM to higher level (Y/N)")
    clabexm = models.BooleanField(verbose_name="Completing Laboratory Exam (Y/N)")
    hemoglobin = models.DecimalField(max_digits=4, decimal_places=1,verbose_name="Hemoglobin")
    urinexam = models.CharField(max_length=255, choices=URIN_EXAM,default="NO/+", verbose_name="Urine exam/Protein Uria (NO/+,++,+++)")
    rpositivepuriatomd = models.BooleanField(verbose_name="Referred  Positive Protin Uria to MD (Y/N)")
    coughmorethantwoweeks= models.BooleanField(verbose_name="cough for more than two weeks(Y/N)")
    rcough = models.BooleanField(verbose_name="Referred cough for more than two week to DOTS Room")
    ttvaccine = models.BooleanField(verbose_name="TT vaccine (Y/N)")
    dangersign = models.BooleanField(verbose_name="Danger signs during pregnancy (Y/N) ")
    typeofdangersign = models.CharField(max_length=255, verbose_name="Type of Danger sign")
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "ANC-FIRST-SESSION"
        verbose_name_plural = "ANC-FIRST-SESSION"

    def __str__(self):
        return self.sessiontype
    
class Gancsecondsession(models.Model):
    SESSION_TYPE = [
        ("GROUP-ANC", "GROUP-ANC"),
    ]

    SESSION_ROUND = [
        ("SECOND-SESSION", "SECOND-SESSION"),
    ]

    INDIVIDUAL_ATTENDANCE = [
        ("GROUP", "GROUP"),
        ("INDIVIDUAL", "INDIVIDUAL"),
        ("ABSENT", "ABSENT"),
    ]

    URIN_EXAM = [
        ("NO/+", "NO/+"),
        ("++", "++"),
        ("+++", "+++"),
    ]

    registerid = models.ForeignKey(
        Gancenrollment,
        on_delete=models.CASCADE,
        verbose_name="Register Name"
    )

    sessiontype = models.CharField(
        max_length=225,
        choices=SESSION_TYPE,
        default="GROUP-ANC",
        verbose_name="Session-Type"
    )

    sessionround = models.CharField(
        max_length=255,
        choices=SESSION_ROUND,
        default="SECOND-SESSION",
        verbose_name="Session-Round"
    )

    sessiondate = models.DateField()

    attendance = models.CharField(
        max_length=255,
        choices=INDIVIDUAL_ATTENDANCE,
        default="GROUP",
        verbose_name="Attendance (Group/Individual/Absent)"
    )

    presentga = models.PositiveIntegerField(verbose_name="Present_GA")
    bp = models.CharField(max_length=255)
    dhypertension = models.BooleanField(verbose_name="Diagnosed with hypertension (Y/N)")
    rhypertensiontoMD = models.BooleanField(verbose_name="Referred  hypertension to MD (Y/N)")
    weight = models.PositiveIntegerField(verbose_name="Weight")
    anemia = models.BooleanField(verbose_name="Anemia (Y/N)")
    ironfolate = models.BooleanField(verbose_name="Iron Folate/routine Dose(Y/N)")
    ironfolatepluswomen = models.BooleanField(verbose_name="Iron folate (30+) for anemic woman(Y/N)")
    pcalcium = models.BooleanField(verbose_name="Prescribe-Calcium(Y/N)")
    acalcium = models.BooleanField(verbose_name="absorbed calcium in the last month(Y/N)")
    mebendazole = models.BooleanField(verbose_name="Mebendazole (Y/N)")
    muac = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        verbose_name="MUAC"
    )
    dmam = models.BooleanField(verbose_name="Diagnosed with MAM (Y/N)")
    rmam = models.BooleanField(verbose_name="Refer MAM to Nutrition Counsellor (Y/N))")
    dsam = models.BooleanField(verbose_name="Diagnosed with SAM (Y/N)")
    rsam = models.BooleanField(verbose_name="Refer SAM to higher level (Y/N)")
    urinexam = models.CharField(
        max_length=255,
        choices=URIN_EXAM,
        default="NO/+",
        verbose_name="Urine exam/Protein Uria (NO/+,++,+++)"
    )

    rpositivepuriatomd = models.BooleanField(verbose_name="Referred  Positive Protin Uria to MD (Y/N)")
    coughmorethantwoweeks = models.BooleanField(verbose_name="cough for more than two weeks(Y/N)")
    rcough = models.BooleanField(verbose_name="Referred cough for more than two week to DOTS Room")
    ttvaccine = models.BooleanField(verbose_name="TT vaccine (Y/N)")
    dangersign = models.BooleanField(verbose_name="Danger signs during pregnancy (Y/N)")
    typeofdangersign = models.CharField(
        max_length=255,
        verbose_name="Type of Danger sign",
        blank=True,
        null=True
    )

    remarks = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "ANC-SECOND-SESSION"
        verbose_name_plural = "ANC-SECOND-SESSION"

    def __str__(self):
        return self.sessiontype
    
class Gancthirdsession(models.Model):
    registerid = models.ForeignKey(Gancenrollment, on_delete=models.CASCADE, verbose_name="Register Name")
    sessiontype = models.TextField()
    sessionround = models.IntegerField()
    sessiondate = models.DateField()
    attendance = models.TextField(verbose_name="Attendance (Group/Individual/No)")
    presentga = models.IntegerField(verbose_name="Present_GA")
    bp = models.TextField()
    dhypertension = models.TextField(verbose_name="Diagnosed with hypertension (Y/N)")
    rhypertensiontoMD = models.TextField(verbose_name="Referred  hypertension to MD (Y/N)")
    weight = models.IntegerField(verbose_name="Weight")
    anemia = models.TextField(verbose_name="Anemia (Y/N)")
    ironfolate = models.TextField(verbose_name="Iron Folate/routine Dose(Y/N)")
    ironfolatepluswomen = models.TextField(verbose_name="Iron folate (30+) for anemic woman(Y/N)")
    pcalcium = models.TextField(verbose_name="Prescribe-Calcium(Y/N)")
    acalcium = models.TextField(verbose_name="absorbed calcium in the last month(Y/N)")
    muac = models.TextField(verbose_name="MUAC")
    dmam = models.TextField(verbose_name="Diagnosed with MAM (Y/N)")
    rmam = models.TextField(verbose_name="Refer MAM to Nutrition Counsellor (Y/N))")
    dsam = models.TextField(verbose_name="Diagnosed with SAM (Y/N)")
    rsam = models.TextField(verbose_name="Refer SAM to higher level (Y/N)")
    antedepressionscreening = models.TextField( verbose_name="Antenatal Depression Screening (Y/N)")
    antedepressiondiagnosed = models.TextField( verbose_name="Antenatal Depression Diagnosed (Y/N)")
    rpsychosocialcounselor = models.TextField( verbose_name="Refer to the psychosocial counselor (Y/N)")
    urinexam = models.TextField(verbose_name="Urine exam/Protein Uria (NO/+,++,+++)")
    rpositivepuriatomd = models.TextField(verbose_name="Referred  Positive Protin Uria to MD (Y/N)")
    coughmorethantwoweeks= models.TextField(verbose_name="cough for more than two weeks(Y/N)")
    rcough = models.TextField(verbose_name="Referred cough for more than two week to DOTS Room")
    ttvaccine = models.TextField(verbose_name="TT vaccine (Y/N)")
    dangersign = models.TextField(verbose_name="Danger signs during pregnancy (Y/N) ")
    typeofdangersign = models.TextField(verbose_name="Type of Danger sign") 
    birthplanningcounseling = models.TextField(verbose_name="Birth Planning Counseling (Y/N) ") 
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "ANC-THIRD-SESSION"
        verbose_name_plural = "ANC-THIRD-SESSION"

    def __str__(self):
        return self.sessiontype

class Gancfouthsession(models.Model):
    registerid = models.ForeignKey(Gancenrollment, on_delete=models.CASCADE, verbose_name="Register Name")
    sessiontype = models.TextField()
    sessionround = models.IntegerField()
    sessiondate = models.DateField()
    attendance = models.TextField(verbose_name="Attendance (Group/Individual/No)")
    presentga = models.IntegerField(verbose_name="Present_GA")
    bp = models.TextField()
    dhypertension = models.TextField(verbose_name="Diagnosed with hypertension (Y/N)")
    rhypertensiontoMD = models.TextField(verbose_name="Referred  hypertension to MD (Y/N)")
    weight = models.IntegerField(verbose_name="Weight")
    anemia = models.TextField(verbose_name="Anemia (Y/N)")
    ironfolate = models.TextField(verbose_name="Iron Folate/routine Dose(Y/N)")
    ironfolatepluswomen = models.TextField(verbose_name="Iron folate (30+) for anemic woman(Y/N)")
    pcalcium = models.TextField(verbose_name="Prescribe-Calcium(Y/N)")
    acalcium = models.TextField(verbose_name="absorbed calcium in the last month(Y/N)")
    muac = models.TextField(verbose_name="MUAC")
    dmam = models.TextField(verbose_name="Diagnosed with MAM (Y/N)")
    rmam = models.TextField(verbose_name="Refer MAM to Nutrition Counsellor (Y/N))")
    dsam = models.TextField(verbose_name="Diagnosed with SAM (Y/N)")
    rsam = models.TextField(verbose_name="Refer SAM to higher level (Y/N)")
    antedepressionscreening = models.TextField( verbose_name="Antenatal Depression Screening (Y/N)")
    antedepressiondiagnosed = models.TextField( verbose_name="Antenatal Depression Diagnosed (Y/N)")
    rpsychosocialcounselor = models.TextField( verbose_name="Refer to the psychosocial counselor (Y/N)")
    urinexam = models.TextField(verbose_name="Urine exam/Protein Uria (NO/+,++,+++)")
    rpositivepuriatomd = models.TextField(verbose_name="Referred  Positive Protin Uria to MD (Y/N)")
    coughmorethantwoweeks= models.TextField(verbose_name="cough for more than two weeks(Y/N)")
    rcough = models.TextField(verbose_name="Referred cough for more than two week to DOTS Room")
    ttvaccine = models.TextField(verbose_name="TT vaccine (Y/N)")
    dangersign = models.TextField(verbose_name="Danger signs during pregnancy (Y/N) ")
    typeofdangersign = models.TextField(verbose_name="Type of Danger sign") 
    birthplanningcounseling = models.TextField(verbose_name="Birth Planning Counseling (Y/N) ") 
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "ANC-FOURTH-SESSION"
        verbose_name_plural = "ANC-FOURTH-SESSION"

    def __str__(self):
        return self.sessiontype

class Gancdelivery(models.Model):
    registerid = models.ForeignKey(Gancenrollment, on_delete=models.CASCADE, verbose_name="Register Name")
    
    PLACE_OF_DELIVERY_CHOICES = [
        ("home", "Home"),
        ("hf", "Health Facility"),
    ]

    TYPE_OF_DELIVERY_CHOICES = [
        ("svd", "Spontaneous Vaginal Delivery"),
        ("assisted", "Assisted Vaginal Delivery"),
        ("c_section", "C-Section"),
        ("other", "Other"),
    ]

    PPFP_METHOD_CHOICES = [
        ("lam", "LAM"),
        ("implant", "Implant"),
        ("ppiucd", "PPIUCD"),
        ("tubal_ligation", "Tubal Ligation"),
    ]

    date_of_delivery = models.DateField(verbose_name="Date of Delivery")
    gestational_age_at_delivery = models.PositiveIntegerField(
        verbose_name="Gestational Age at Delivery (weeks)"
    )

    place_of_delivery = models.CharField(
        max_length=10,
        choices=PLACE_OF_DELIVERY_CHOICES,
        verbose_name="Place Of Delivery"
    )

    type_of_delivery = models.CharField(
        max_length=20,
        choices=TYPE_OF_DELIVERY_CHOICES,
        verbose_name="Type Of Delivery"
    )

    immediate_uterotonic_for_amtsl = models.BooleanField(
        verbose_name="Immediate Uterotonic for AMTSL",
        default=False
    )

    types_of_complication = models.TextField(
        blank=True,
        null=True,
        verbose_name="Types of Complication"
    )

    how_complication_was_managed = models.TextField(
        blank=True,
        null=True,
        verbose_name="How Complication Was Managed"
    )

    maternal_death = models.BooleanField(
        default=False,
        verbose_name="Maternal Death"
    )

    number_of_newborn = models.PositiveIntegerField(
        default=1,
        verbose_name="Number Of Newborn"
    )

    number_of_alive_newborn = models.PositiveIntegerField(
        default=1,
        verbose_name="Number Of Alive Newborn"
    )

    number_of_newborn_death = models.PositiveIntegerField(
        default=0,
        verbose_name="Number Of Newborn Death"
    )

    number_of_fresh_still_birth = models.PositiveIntegerField(
        default=0,
        verbose_name="Number Of Fresh Still Birth"
    )

    early_breastfeeding = models.BooleanField(
        default=False,
        verbose_name="Early Breastfeeding"
    )

    newborn_vaccination_before_discharge = models.BooleanField(
        default=False,
        verbose_name="Newborn Vaccination Before Discharge"
    )

    counseled_on_postpartum_fp_before_discharge = models.BooleanField(
        default=False,
        verbose_name="Counseled on Postpartum FP Before Discharge"
    )

    immediate_ppfp_before_discharge = models.BooleanField(
        default=False,
        verbose_name="Immediate PPFP Before Discharge"
    )

    ppfp_method_taken_before_discharge = models.CharField(
        max_length=20,
        choices=PPFP_METHOD_CHOICES,
        blank=True,
        null=True,
        verbose_name="Which PPFP Method Has Been Taken Before Discharge"
    )

    remark = models.TextField(
        blank=True,
        null=True,
        verbose_name="Remark"
    )

    class Meta:
        verbose_name = "DELIVERY"
        verbose_name_plural = "DELIVERY"

    def __str__(self):
        return f"Delivery Outcome - {self.date_of_delivery}"
    
class GroupPncfirstSession(models.Model):
    registerid = models.ForeignKey(Gancenrollment, on_delete=models.CASCADE, verbose_name="Register Name")
    SESSION_TYPE_CHOICES = [
        ("group", "Group"),
        ("individual", "Individual"),
        ("home_visit", "Home Visit"),
        ("other", "Other"),
    ]

    ATTENDANCE_CHOICES = [
        ("group", "Group"),
        ("individual", "Individual"),
        ("no", "No"),
    ]

    PROTEIN_URIA_CHOICES = [
        ("no", "No"),
        ("+", "+"),
        ("++", "++"),
        ("+++", "+++"),
    ]

    PPFP_METHOD_CHOICES = [
        ("lam", "LAM"),
        ("implant", "Implant"),
        ("ppiucd", "PPIUCD"),
        ("tubal_ligation", "Tubal Ligation"),
        ("injectable", "Injectable"),
        ("pills", "Pills"),
        ("condom", "Condom"),
        ("other", "Other"),
    ]

    session_type = models.CharField(
        max_length=20,
        choices=SESSION_TYPE_CHOICES,
        verbose_name="Session Type"
    )

    session_round = models.PositiveIntegerField(
        verbose_name="Session Round"
    )

    session_date = models.DateField(
        verbose_name="Session Date"
    )

    post_natal_day = models.PositiveIntegerField(
        verbose_name="Post-natal Day"
    )

    attendance = models.CharField(
        max_length=20,
        choices=ATTENDANCE_CHOICES,
        verbose_name="Attendance"
    )

    bp = models.CharField(
        max_length=20,
        verbose_name="BP",
        help_text="Example: 120/80"
    )

    diagnosed_with_hypertension = models.BooleanField(
        default=False,
        verbose_name="Diagnosed with Hypertension"
    )

    referred_hypertension_to_md = models.BooleanField(
        default=False,
        verbose_name="Referred Hypertension to MD"
    )

    muac = models.CharField(
        max_length=20,
        verbose_name="MUAC"
    )

    diagnosed_with_mam = models.BooleanField(
        default=False,
        verbose_name="Diagnosed with MAM"
    )

    refer_mam_to_nutrition_counselor = models.BooleanField(
        default=False,
        verbose_name="Refer MAM to Nutrition Counselor"
    )

    diagnosed_with_sam = models.BooleanField(
        default=False,
        verbose_name="Diagnosed with SAM"
    )

    refer_sam_to_higher_level = models.BooleanField(
        default=False,
        verbose_name="Refer SAM to Higher Level"
    )

    anemia = models.BooleanField(
        default=False,
        verbose_name="Anemia"
    )

    iron_folate_routine_dose = models.BooleanField(
        default=False,
        verbose_name="Iron Folate / Routine Dose"
    )

    iron_folate_plus_for_anemic_woman = models.BooleanField(
        default=False,
        verbose_name="Iron Folate (30+) for Anemic Woman"
    )

    type_of_maternal_danger_sign = models.TextField(
        blank=True,
        null=True,
        verbose_name="Type of Maternal Danger Sign"
    )

    type_of_newborn_danger_sign = models.TextField(
        blank=True,
        null=True,
        verbose_name="Type of Newborn Danger Sign"
    )

    newborn_death = models.BooleanField(
        default=False,
        verbose_name="Newborn Death"
    )

    maternal_death = models.BooleanField(
        default=False,
        verbose_name="Maternal Death"
    )

    newborn_vaccination_completed = models.BooleanField(
        default=False,
        verbose_name="Newborn Vaccination Completed"
    )

    urine_exam = models.BooleanField(
        default=False,
        verbose_name="Urine Exam"
    )

    protein_uria = models.CharField(
        max_length=5,
        choices=PROTEIN_URIA_CHOICES,
        blank=True,
        null=True,
        verbose_name="Protein Uria"
    )

    referred_positive_protein_uria_to_md = models.BooleanField(
        default=False,
        verbose_name="Referred Positive Protein Uria to MD"
    )

    cough_more_than_two_weeks = models.BooleanField(
        default=False,
        verbose_name="Cough for More Than Two Weeks"
    )

    referred_cough_to_dots_room = models.BooleanField(
        default=False,
        verbose_name="Referred Cough to DOTS Room"
    )

    exclusive_breast_feeding = models.BooleanField(
        default=False,
        verbose_name="Exclusive Breast-Feeding"
    )

    chosen_ppfp_method = models.BooleanField(
        default=False,
        verbose_name="Chosen a PPFP Method"
    )

    ppfp_method_taken = models.CharField(
        max_length=30,
        choices=PPFP_METHOD_CHOICES,
        blank=True,
        null=True,
        verbose_name="If Yes, Which Method Was Taken"
    )

    remark = models.TextField(
        blank=True,
        null=True,
        verbose_name="Remark"
    )

    class Meta:
        verbose_name = "PNC-FIRST-SESSION"
        verbose_name_plural = "PNC-FIRST-SESSION"

    def __str__(self):
        return f"{self.session_type} - Round {self.session_round} - {self.session_date}"

class GroupPncsecondSession(models.Model):
    registerid = models.ForeignKey(Gancenrollment, on_delete=models.CASCADE, verbose_name="Register Name")
    SESSION_TYPE_CHOICES = [
        ("group", "Group"),
        ("individual", "Individual"),
        ("home_visit", "Home Visit"),
        ("other", "Other"),
    ]

    ATTENDANCE_CHOICES = [
        ("group", "Group"),
        ("individual", "Individual"),
        ("no", "No"),
    ]

    BIRTH_SPACING_METHOD_CHOICES = [
        ("lam", "LAM"),
        ("implant", "Implant"),
        ("iucd", "IUCD"),
        ("injectable", "Injectable"),
        ("pills", "Pills"),
        ("condom", "Condom"),
        ("tubal_ligation", "Tubal Ligation"),
        ("other", "Other"),
    ]

    sessiontype = models.CharField(
        max_length=20,
        choices=SESSION_TYPE_CHOICES,
        verbose_name="Session Type"
    )

    sessionround = models.PositiveIntegerField(
        verbose_name="Session Round"
    )

    sessiondate = models.DateField(
        verbose_name="Session Date"
    )

    postnatalday = models.PositiveIntegerField(
        verbose_name="Post-natal Day"
    )

    attendance = models.CharField(
        max_length=20,
        choices=ATTENDANCE_CHOICES,
        verbose_name="Attendance"
    )

    bp = models.CharField(
        max_length=20,
        verbose_name="BP",
        help_text="Example: 120/80"
    )

    dhypertension = models.BooleanField(
        default=False,
        verbose_name="Diagnosed with Hypertension (Y/N)"
    )

    rhypertensiontomd = models.BooleanField(
        default=False,
        verbose_name="Referred Hypertension to MD (Y/N)"
    )

    muac = models.CharField(
        max_length=20,
        verbose_name="MUAC"
    )

    dmam = models.BooleanField(
        default=False,
        verbose_name="Diagnosed with MAM (Y/N)"
    )

    rmam = models.BooleanField(
        default=False,
        verbose_name="Refer MAM to Nutrition Counselor (Y/N)"
    )

    dsam = models.BooleanField(
        default=False,
        verbose_name="Diagnosed with SAM (Y/N)"
    )

    rsam = models.BooleanField(
        default=False,
        verbose_name="Refer SAM to Higher Level (Y/N)"
    )

    anemia = models.BooleanField(
        default=False,
        verbose_name="Anemia (Y/N)"
    )

    ironfolate = models.BooleanField(
        default=False,
        verbose_name="Iron Folate / Routine Dose (Y/N)"
    )

    ironfolatepluswomen = models.BooleanField(
        default=False,
        verbose_name="Iron Folate (30+) for Anemic Woman (Y/N)"
    )

    postnataldepressiondiagnosed = models.BooleanField(
        default=False,
        verbose_name="Postnatal Depression Diagnosed (Y/N)"
    )

    rpsychosocialcounselor = models.BooleanField(
        default=False,
        verbose_name="Refer to Psychosocial Counselor (Y/N)"
    )

    typeofmaternaldangersign = models.TextField(
        blank=True,
        null=True,
        verbose_name="Type of Maternal Danger Sign"
    )

    typeofnewborndangersign = models.TextField(
        blank=True,
        null=True,
        verbose_name="Type of Newborn Danger Sign"
    )

    newborndeath = models.BooleanField(
        default=False,
        verbose_name="Newborn Death (Y/N)"
    )

    maternaldeath = models.BooleanField(
        default=False,
        verbose_name="Maternal Death (Y/N)"
    )

    newbornvaccinationcompleted = models.BooleanField(
        default=False,
        verbose_name="Newborn Vaccination Completed (Y/N)"
    )

    coughmorethantwoweeks = models.BooleanField(
        default=False,
        verbose_name="Cough for More Than Two Weeks (Y/N)"
    )

    rcough = models.BooleanField(
        default=False,
        verbose_name="Referred Cough for More Than Two Weeks to DOTS Room (Y/N)"
    )

    exclusivebreastfeeding = models.BooleanField(
        default=False,
        verbose_name="Exclusive Breast-Feeding (Y/N)"
    )

    birthspacingmethodchosen = models.BooleanField(
        default=False,
        verbose_name="Birth Spacing Method Chosen (Y/N)"
    )

    birthspacingmethod = models.CharField(
        max_length=30,
        choices=BIRTH_SPACING_METHOD_CHOICES,
        blank=True,
        null=True,
        verbose_name="The Birth Spacing Method Chosen"
    )

    remark = models.TextField(
        blank=True,
        null=True,
        verbose_name="Remark"
    )

    class Meta:
        verbose_name = "PNC-SECOND-SESSION"
        verbose_name_plural = "PNC-SECOND-SESSION"

    def __str__(self):
        return f"{self.sessiontype} - Round {self.sessionround} - {self.sessiondate}"
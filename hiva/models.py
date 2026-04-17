from django.conf import settings
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Province(models.Model):
    name = models.CharField(max_length=200, unique=True)
    provinceshortname = models.CharField(max_length=200, null=True, blank=True)
    description = models.TextField(blank=True)
    provincecode = models.IntegerField(blank=True, null=True)
    province = models.CharField(blank=True, null=True)
    provinceDari = models.CharField(blank=True, null=True)
    provincePashto = models.CharField(blank=True, null=True)
    phase = models.IntegerField(blank=True, null=True)

    class Meta:
        verbose_name = "PROVINCE"
        verbose_name_plural = "PROVINCE"

    def __str__(self):
        return self.name

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    province = models.ForeignKey(Province, on_delete=models.PROTECT, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} -> {self.province or 'No province'}"
    
class District(models.Model):
    provincefk = models.ForeignKey(Province, on_delete=models.CASCADE, default=1)
    name = models.TextField(max_length=200, unique=True, verbose_name="District Name")
    description = models.TextField(blank=True)
    districtcode = models.IntegerField(blank=True, null=True)
    district = models.CharField(blank=True, null=True)
    districtdari = models.CharField(blank=True, null=True)
    districtpashto = models.CharField(blank=True, null=True)

    class Meta:
        verbose_name = "DISTRICT"
        verbose_name_plural = "DISTRICT"

    def __str__(self):
        return self.name

class Facilitytype(models.Model):
    name = models.CharField(max_length=200, unique=True)
    shortname = models.TextField(blank=True)
    namedari = models.CharField(blank=True, null=True)
    namepashto = models.CharField(blank=True, null=True)

    class Meta:
        verbose_name = "HEALTH FACILITY TYPE"
        verbose_name_plural = "HEALTH FACILITY TYPE"

    def __str__(self):
        return self.name
    
class Facility(models.Model):
    districtfk = models.ForeignKey(District, on_delete=models.CASCADE, default=1, verbose_name='District')
    facilitytypefk = models.ForeignKey(Facilitytype, on_delete=models.CASCADE, default=1, verbose_name='Facility Type')
    name = models.TextField(max_length=200, unique=True, verbose_name='Facility Name')
    description = models.TextField(blank=True)
    hfcode = models.IntegerField(blank=True, null=True)
    namedari = models.CharField(blank=True, null=True)
    namepashto = models.CharField(blank=True, null=True)
    averagetimetoarive = models.CharField(blank=True, null=True)
    distincefromcity = models.CharField(blank=True, null=True)
    selectionphase = models.IntegerField(blank=True, null=True)
    catchment = models.BigIntegerField(blank=True, null=True)
    latitude = models.DecimalField(max_digits=22, decimal_places=16, blank=True, null=True)
    longitude = models.DecimalField(max_digits=22, decimal_places=16, blank=True, null=True)
    selectiondate = models.DateField(blank=True, null=True)
    dropoutdate = models.DateField(blank=True, null=True)
    aim = models.BooleanField(blank=True, null=True, verbose_name='AIM')
    safesurgery = models.BooleanField(blank=True, null=True, verbose_name='Safe Surgery')
    ganc = models.BooleanField(blank=True, null=True, verbose_name='G-ANC/G-PNC')
    afiat = models.BooleanField(blank=True, null=True, verbose_name='AFIAT')
    skilllab = models.BooleanField(blank=True, default=False, verbose_name="Skill Lab")
    aimphase = models.IntegerField(blank=True, null=True, verbose_name="AIM Phase")
    nbcc = models.BooleanField(blank=True, null=True, verbose_name="NBCC")
    sncu = models.BooleanField(blank=True, null=True, verbose_name="SNCU")
    kmc = models.BooleanField(blank=True, null=True, verbose_name="KMC")

    class Meta:
        verbose_name = "HEALTH FACILITY"
        verbose_name_plural = "HEALTH FACILITY"  

    def __str__(self):
        return self.name

class Implementor(models.Model):
    name = models.CharField(max_length=200, unique=True, 
    verbose_name="Service Provider(NGO)")
    shortname = models.TextField(blank=True)
    provinceimplementor = models.ForeignKey(
        Province, on_delete=models.CASCADE, 
        null=True, blank=True)

    class Meta:
        verbose_name = "IMPLEMENTER"
        verbose_name_plural = "IMPLEMENTER"

    def __str__(self):
        return self.name
    
class Position(models.Model):
    name = models.CharField(verbose_name="Position")

    class Meta:
        verbose_name = "STAFF PROFESSION"
        verbose_name_plural = "STAFF PROFESSION"

    def __str__(self):
        return self.name
    
class Assessor(models.Model):
    name = models.CharField(max_length=200, verbose_name="Assessor Name")
    contact = models.TextField(blank=True)
    email = models.CharField(blank=True, null=True)
    tazkira = models.CharField(blank=True, null=True)
    gender = models.BooleanField(choices=[
            (True, "Female"),
            (False, "Male"),
        ],
        default=True,
        verbose_name="Gender", 
        blank=True, null=True)
    implementer = models.ForeignKey(Implementor, on_delete=models.CASCADE, null=True, blank=True)
    province = models.ForeignKey(Province, on_delete=models.CASCADE, null=True, blank=True)
    status = models.BooleanField(choices=[
            (True, "Active"),
            (False, "Inactive"),
        ],
        default=True,
        verbose_name="Status", 
        blank=True, null=True)
    phaseonecloseout = models.DateField(blank=True, null=True)
    continuetophase2 = models.BooleanField(  choices=[
            (True, "Yes"),
            (False, "No"),
        ],
        default=False,
        verbose_name="Continued to Phase Two", 
        blank=True, null=True)
    note = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "CLINICAL MENTOR"
        verbose_name_plural = "CLINICAL MENTOR"

    def __str__(self):
        return self.name

class Assessmenttype(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name="Assessment Type")
    shortname = models.TextField(blank=True)

    class Meta:
        verbose_name = "ASSESSMENT TYPE"
        verbose_name_plural = "ASSESSMENT TYPE"

    def __str__(self):
        return self.name
    
class Area(models.Model):
    name = models.TextField(max_length=200, verbose_name="Thematic Area")
    shortname = models.TextField(blank=True)
    area_namepashto = models.TextField(max_length=200, null=True, blank=True, verbose_name="Thematic Area Pashto")
    area_namedari= models.TextField(max_length=200, null=True, blank=True, verbose_name="Thematic Area Dari")

    class Meta:
        verbose_name = "THEMATIC AREA"
        verbose_name_plural = "THEMATIC AREA"

    def __str__(self):
        return self.name
    
class Section(models.Model):
    areafk = models.ForeignKey(Area, on_delete=models.CASCADE, null=True, blank=True)
    name = models.TextField(verbose_name="Section")
    shortname = models.TextField(blank=True)
    section_namepashto = models.TextField(max_length=200, null=True, blank=True, verbose_name="Section Pashto")
    section_namedari= models.TextField(max_length=200, null=True, blank=True, verbose_name="Section Dari")

    class Meta:
        verbose_name = "HQIP SECTION"
        verbose_name_plural = "HQIP SECTION"

    def __str__(self):
        return self.name

class Standards(models.Model):
    sectionfk = models.ForeignKey(Section, on_delete=models.CASCADE, null=True, blank=True)
    name = models.TextField(verbose_name="Standard")
    shortname = models.TextField(blank=True)
    standard_namepashto = models.TextField(max_length=200, null=True, blank=True, verbose_name="Standard Pashto")
    standard_namedari= models.TextField(max_length=200, null=True, blank=True, verbose_name="Standard Dari")

    class Meta:
        verbose_name = "HQIP STANDARD"
        verbose_name_plural = "HQIP STANDARD"

    def __str__(self):
        return self.name
    
class Score(models.Model):
    name = models.TextField(verbose_name="Score")
    shorname = models.TextField(blank=True)
    value = models.IntegerField(default=0)
    score_namepashto = models.TextField(max_length=200, null=True, blank=True, verbose_name="Score Pashto")
    score_namedari= models.TextField(max_length=200, null=True, blank=True, verbose_name="Score Dari")

    class Meta:
        verbose_name = "HQIP SCORE"
        verbose_name_plural = "HQIP SCORE"

    def __str__(self):
        return self.name
     
class Criteria(models.Model):
    standardfk = models.ForeignKey(Standards, on_delete=models.CASCADE, null=True, blank=True)
    scorefk = models.ForeignKey(Score, on_delete=models.CASCADE)
    name = models.TextField(verbose_name="Verification Criteria")
    shortname = models.TextField(blank=True)
    criteria_namepashto = models.TextField(max_length=200, null=True, blank=True, verbose_name="Criteria Pashto")
    criteria_namedari = models.TextField(max_length=200, null=True, blank=True, verbose_name="Criteria Dari")
    createdby = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "HQIP CRITERIA"
        verbose_name_plural = "HQIP CRITERIA"

    def __str__(self):
        return self.name
    
class HQIPAssessmentHeader(models.Model):
    facilityfk = models.ForeignKey(Facility, on_delete=models.CASCADE, verbose_name="Health Facility")
    assesorfk = models.ForeignKey(Assessor, on_delete=models.CASCADE, verbose_name="Assessor")
    implementorfk = models.ForeignKey(Implementor, on_delete=models.CASCADE, verbose_name="Implementor")
    assessmenttype = models.ForeignKey(Assessmenttype, on_delete=models.CASCADE, verbose_name="Assessment Type")
    assessmentdate = models.DateField(verbose_name="Assessment Start Date")
    assessmentend_date = models.DateField(verbose_name="Assessment End Date")
    areafk = models.ForeignKey(Area, on_delete=models.CASCADE, verbose_name="Thematic Area")
    assessmentteam = models.TextField(
        max_length=200, blank=True, null=True,
        verbose_name="Assessment Team")
    is_RCAduringtheassessment = models.BooleanField(
        choices=[
            (True, "Yes"),
            (False, "No"),
        ],
        default=False,
        verbose_name="RCA conducted", 
        blank=True, null=True)
    
    created_by = models.ForeignKey(
    settings.AUTH_USER_MODEL, 
    on_delete=models.PROTECT,
    related_name="hqip_assessments_created", 
    editable=False, null=True, blank=True)

    created_at = models.DateTimeField(
    default=timezone.now, editable=False)

    updated_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.PROTECT,
    related_name="hqip_assessments_updated",
    editable=False,
    null=True,
    blank=True)

    updated_at = models.DateTimeField(
        auto_now=True, 
        editable=False)
    
    def clean(self):
        super().clean()

        if self.assessmentdate and self.assessmentend_date:
            if self.assessmentend_date < self.assessmentdate:
                raise ValidationError({
                    "assessmentend_date": "Assessment End Date cannot be earlier than Assessment Start Date."
                })

    class Meta:
        verbose_name = "HQIP ASSESSMENT"
        verbose_name_plural = "HQIP ASSESSMENT"
        constraints = [
            models.UniqueConstraint(
                fields=["facilityfk", "assessmenttype", "assessmentdate", "areafk"],
                name="uniq_hdr_fac_type_date_area"
            )
        ]

    def __str__(self):
        return f"{self.facilityfk} | {self.assessmenttype} | {self.assessmentdate} | {self.areafk}"

class HQIPAssessment(models.Model):
    header = models.ForeignKey(HQIPAssessmentHeader, on_delete=models.CASCADE, related_name="lines", null=True, blank=True)
    criteriafk = models.ForeignKey(Criteria, on_delete=models.CASCADE)
    scorefk = models.ForeignKey(Score, on_delete=models.PROTECT, null=True, blank=True)
    #remarks = models.TextField(max_length=10, blank=True, null=True)

    class Meta:
        verbose_name = "HQIP ASSESSMENT DETAILS"
        verbose_name_plural = "HQIP ASSESSMENT DETAILS"
        constraints = [
            models.UniqueConstraint(fields=["header", "criteriafk"], name="uniq_line_per_criteria")
        ]

    def __str__(self):
        try:
            sec = self.criteriafk.standardfk.sectionfk.shortname or self.criteriafk.standardfk.sectionfk.name
            std = self.criteriafk.standardfk.shortname or self.criteriafk.standardfk.name
            cri = self.criteriafk.shortname or self.criteriafk.name
            return f"{sec} > {std} > {cri}"
        except Exception:
            return f"Assessment #{self.pk}"
   
class Participationtype(models.Model):
    name = models.TextField()

    class Meta:
        verbose_name = "PARTICIPANT TYPE"
        verbose_name_plural = "PARTICIPANT TYPE"

    def __str__(self):
        return self.name

class Trainingheader(models.Model):
    trainingname = models.TextField()
    trainingvenue = models.TextField()
    trainingstartdate = models.DateField()
    trainingenddate = models.DateField()
    expectednumberofparticipant = models.IntegerField(blank=True, null=True)
    traingfocalpoint = models.CharField(max_length=200, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "TRAINING TITLE"
        verbose_name_plural = "TRAINING TITLE"

    def __str__(self):
        return self.trainingname

class Participanteducation(models.Model):
    name = models.TextField()
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "PARTICIPANT EDUCATION"
        verbose_name_plural = "PARTICIPANT EDUCATION"

    def __str__(self):
        return self.name
    
class Participantposition(models.Model):
    name = models.TextField()
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "PARTICIPANT POSITION"
        verbose_name_plural = "PARTICIPANT POSITION"

    def __str__(self):
        return self.name

class Training(models.Model):
    trainingheader = models.ForeignKey(Trainingheader, on_delete=models.CASCADE, blank=True, null=True)
    participantprovinice = models.ForeignKey(Province, on_delete=models.CASCADE)
    participantdistrict = models.ForeignKey(District, on_delete=models.CASCADE)
    currentaddress = models.CharField(max_length=200, blank=True, null=True)
    hivastaff = models.CharField()
    hivaclinicalstaff = models.ForeignKey(Assessor, on_delete=models.CASCADE, blank=True, null=True)
    firstname = models.CharField()
    lastname = models.CharField()
    fathername = models.CharField()
    nid = models.CharField()
    gender = models.CharField()
    contactnumber = models.CharField(blank=True, null=True)
    participantemail = models.CharField(blank=True, null=True)
    Serviceprovider = models.ForeignKey(Implementor, on_delete=models.CASCADE, blank=True, null=True)
    participationtype = models.ForeignKey(Participationtype, on_delete=models.CASCADE)
    participanteducation = models.ForeignKey(Participanteducation, on_delete=models.CASCADE)
    participantposition = models.ForeignKey(Participantposition, on_delete=models.CASCADE, blank=True, null=True)
    trainingbatch = models.IntegerField(blank=True, null=True)
    thematicarea = models.ForeignKey(Area, on_delete=models.CASCADE)
    observation = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "TRAINING"
        verbose_name_plural = "TRAINING"

    def __str__(self):
        return self.firstname

class FacilityStaff(models.Model):

    GENDER_CHOICES = [
        ("Female", "Female"),
        ("Male", "Male"),
    ]

    first_name = models.CharField(
        max_length=100,
        verbose_name="First Name"
    )

    last_name = models.CharField(
        max_length=100,
        verbose_name="Last Name"
    )

    father_name = models.CharField(
        max_length=100,
        verbose_name="Father_name"
    )

    gender = models.CharField(
        max_length=7,
        choices=GENDER_CHOICES,
        blank=True,
        null=True,
        verbose_name="Gender"
    )

    email = models.EmailField(
        blank=True,
        null=True,
        verbose_name="Email"
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Phone"
    )

    position = models.ForeignKey(
        "hiva.Position",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="facility_staff_positions",
        verbose_name="Position"
    )

    facility = models.ForeignKey(
        "hiva.Facility",
        on_delete=models.PROTECT,
        related_name="facility_staffs",
        verbose_name="Facility"
    )

    code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Staff Code"
    )

    tazkira_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Tazkira Number"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Is Active"
    )

    year_of_birth = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Year of Birth"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True, editable=False,
        related_name="created_%(class)s_records"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True, editable=False,
        related_name="updated_%(class)s_records"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At"
    )

    record_status = models.IntegerField(
        default=1, editable=False,
        verbose_name="Record Status"
    )

    verified = models.BooleanField(
        default=True, editable=False,
        verbose_name="Verified"
    )

    class Meta:
        #abstract = True
        db_table = "FacilityStaffs"
        verbose_name = "FACILITY STAFF"
        verbose_name_plural = "FACILITY STAFF"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class QICommittee(models.Model):

    ROLE_CHOICES = [
        ("Head", "Head"),
        ("Member", "Member"),
        ("Focalpoint", "Focalpoint"),
        ("Other", "Other"),
    ]

    facility = models.ForeignKey(
        "hiva.Facility",
        on_delete=models.PROTECT,
        related_name="qi_committees",
        verbose_name="HEALTH FACILITY"
    )

    facility_staff = models.ForeignKey(
        "hiva.FacilityStaff",
        on_delete=models.PROTECT,
        related_name="qi_committee_memberships",
        verbose_name="HEALTH FACILITY STAFF"
    )

    role = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES,
        verbose_name="Committee Role"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True, editable=False,
        related_name="created_%(class)s_records"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True, editable=False,
        related_name="updated_%(class)s_records"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At"
    )

    record_status = models.IntegerField(
        default=1, editable=False,
        verbose_name="Record Status"
    )

    class Meta:
        db_table = "QICommittee"
        verbose_name = "QIC MEMBERS"
        verbose_name_plural = "QIC MEMBERS"

    def __str__(self):
        return f"{self.facility} - {self.facility_staff} ({self.role})"

class Qicdataset(models.Model):
    qiccommdate = models.DateField()
    qicfacility = models.ForeignKey(Facility, on_delete=models.CASCADE)
    qicdatacollector = models.ForeignKey(Assessor, on_delete=models.CASCADE)
    qicimplementor = models.ForeignKey(Implementor, on_delete=models.CASCADE, blank=True, null=True)
    qictoravailvalue = models.IntegerField(default=0, verbose_name="1. Are the Terms of Reference (TOR) of QI focal point and QI committee available at HF?")
    qiclastmonthvalue = models.IntegerField(default=0, verbose_name="2. Was the QI committee’s meeting conducted in last month?")
    qicmmavialvalue = models.IntegerField(default=0, verbose_name="3. Are the meeting minutes of QI committee’s last month’s meeting available.")
    qicmmsignedvalue = models.IntegerField(default=0, verbose_name="4. Did the participants of the QI committee sign the meeting minutes of last month meeting?")
    qicmmdatausevalue = models.IntegerField(default=0, verbose_name="5. Were data use discussed in the last month QI committee’s meeting? Please refer to the meeting minutes of last month")
    qichqiptollavailvalue = models.IntegerField(default=0, verbose_name="6. Is a copy of the Harmonized Quality Improvement Program (HQIP) tool available and accessible at the HF? ")
    qicpipavailvalue = models.IntegerField(default=0, verbose_name="7. Is a Performance Improvement Plan (PIP available at the HF?")
    qicpipupdatedvalue = models.IntegerField(default=0, verbose_name="8. Has the PIP been updated in last month QI committee’s meeting? Write number of completed corrective actions")
    qicngoinvolvedvalue = models.IntegerField(default=0, verbose_name="9. Has the NGO been involved in the corrective actions completed in last month?")
    qicpeertopeeravailvalue = models.IntegerField(default=0, verbose_name="10. Have peer to peer learning sessions been conducted within the health facility during the last month? i.e. learning sessions conducted by QI focal point or QI committee members for the HF staff")
    qicmenteelogbookavialvalue = models.IntegerField(default=0, verbose_name="11. Is the mentee logbook available in the HF?")
    qicmenteelogbookupdatedvalue = models.IntegerField(default=0, verbose_name="12. Has the mentee logbook been updated with the learning sessions conducted in last month and signed by the mentors of the HF?")
    qicmetwithhealthshuravalue = models.IntegerField(default=0, verbose_name="13. Has the QI committee met the HF Shura-e-Sihie in last month? Please refer to the related meeting minutes")
    qichealthshurainvolvedincorractvalue = models.IntegerField(default=0, verbose_name="14. Has the HF Shura-e-Sihie been involved in the completion of the corrective actions in last month?")
    qictotalquestions = models.IntegerField(default=0)
    remarks = models.TextField(blank=True, null=True)
    image = models.FileField(upload_to='qic-minutes/', null=True, blank=True)  # Files are stored in the media directory by default
    uploaded_at = models.DateField(auto_now_add=True, null=True, blank=True)

    class Meta:
        verbose_name = "QIC"
        verbose_name_plural = "QIC"

    def __str__(self):
        return f"{self.qicfacility} {self.qiccommdate}" 
    
MONTH_CHOICES = [
        ("1", "January"), ("2", "February"), ("3", "March"), ("4", "April"),
        ("5", "May"), ("6", "June"), ("7", "July"), ("8", "August"),
        ("9", "September"), ("10", "October"), ("11", "November"), ("12", "December"),
    ]
YCHOICES = [(2026, "2026"), (2026, "2026"), (2027, "2027")]

MATERNAL_DEATH_CAUSE_CATEGORY_CHOICES = [
    ("hemorrhage", "Obstetric hemorrhage"),
    ("hypertensive", "Hypertensive disorders in pregnancy"),
    ("sepsis", "Sepsis / infection"),
    ("obstructed_rupture", "Obstructed labor / uterine rupture"),
    ("abortion", "Abortion-related complications"),
    ("embolism", "Embolism"),
    ("indirect", "Indirect medical cause"),
    ("unknown", "Unknown / under investigation"),
    ("other", "Other specified cause"),
]

MATERNAL_DEATH_SPECIFIC_CAUSE_CHOICES = [
    ("pph", "Postpartum hemorrhage (PPH)"),
    ("uterine_atony", "Uterine atony"),
    ("abruptio_placenta", "Abruptio placenta"),
    ("placenta_previa", "Placenta previa"),
    ("retained_placenta", "Retained placenta"),
    ("other_hemorrhage", "Other obstetric hemorrhage"),

    ("severe_pre_eclampsia", "Severe pre-eclampsia"),
    ("eclampsia", "Eclampsia"),
    ("hellp", "HELLP syndrome"),
    ("other_hypertensive", "Other hypertensive disorder"),

    ("puerperal_sepsis", "Puerperal sepsis"),
    ("post_abortion_sepsis", "Post-abortion sepsis"),
    ("postoperative_infection", "Postoperative infection"),
    ("other_sepsis", "Other maternal infection"),

    ("obstructed_labor", "Obstructed labor"),
    ("prolonged_labor", "Prolonged labor"),
    ("uterine_rupture", "Uterine rupture"),
    ("other_obstructed_rupture", "Other labor-related complication"),

    ("abortion_hemorrhage", "Hemorrhage after abortion"),
    ("unsafe_abortion", "Unsafe abortion complication"),
    ("incomplete_abortion", "Incomplete abortion complication"),
    ("other_abortion", "Other abortion-related complication"),

    ("pulmonary_embolism", "Pulmonary embolism"),
    ("amniotic_fluid_embolism", "Amniotic fluid embolism"),
    ("other_embolism", "Other embolism"),

    ("severe_anemia", "Severe anemia"),
    ("cardiac_disease", "Cardiac disease"),
    ("respiratory_disease", "Respiratory disease / COPD"),
    ("liver_disease_pregnancy", "Liver disease in pregnancy"),
    ("renal_disease", "Renal disease"),
    ("malaria", "Malaria"),
    ("tuberculosis", "Tuberculosis"),
    ("diabetes", "Diabetes complication"),
    ("other_indirect", "Other indirect medical cause"),

    ("unknown_under_investigation", "Unknown / under investigation"),
    ("other_specified", "Other specified cause"),
]

MATERNAL_DEATH_CONTRIBUTING_FACTOR_CHOICES = [
    ("delay_seek_care", "Delay in deciding to seek care"),
    ("delay_reach_facility", "Delay in reaching facility"),
    ("delay_receive_care", "Delay in receiving appropriate care"),
    ("lack_medicines", "Lack of essential medicines"),
    ("lack_blood", "Lack of blood / transfusion service"),
    ("lack_equipment", "Lack of equipment / supplies"),
    ("referral_delay", "Referral delay"),
    ("staffing_gap", "Human resource / staffing gap"),
    ("monitoring_gap", "Monitoring / early detection gap"),
    ("clinical_management_gap", "Gap in timely clinical management"),
    ("documentation_gap", "Documentation gap"),
    ("community_awareness_gap", "Community awareness gap"),
    ("other_system_gap", "Other system gap"),
]

MATERNAL_DEATH_PREVENTABILITY_CHOICES = [
    ("likely_preventable", "Likely preventable"),
    ("possibly_preventable", "Possibly preventable"),
    ("not_preventable", "Not preventable"),
    ("unclear", "Unclear"),
]

MATERNAL_DEATH_TIMING_CHOICES = [
    ("during_pregnancy", "During pregnancy"),
    ("during_labor", "During labor / childbirth"),
    ("within_24h_postpartum", "Within 24 hours postpartum"),
    ("day_2_7_postpartum", "2–7 days postpartum"),
    ("day_8_42_postpartum", "8–42 days postpartum"),
    ("unknown", "Unknown"),
]

MATERNAL_DEATH_PLACE_CHOICES = [
    ("home", "At home"),
    ("in_transit", "On the way / in transit"),
    ("facility", "Health facility"),
    ("referral_facility", "Referral facility"),
    ("unknown", "Unknown"),
]

SPECIFIC_CAUSE_CATEGORY_MAP = {
    "pph": "hemorrhage",
    "uterine_atony": "hemorrhage",
    "abruptio_placenta": "hemorrhage",
    "placenta_previa": "hemorrhage",
    "retained_placenta": "hemorrhage",
    "other_hemorrhage": "hemorrhage",
    "severe_pre_eclampsia": "hypertensive",
    "eclampsia": "hypertensive",
    "hellp": "hypertensive",
    "other_hypertensive": "hypertensive",
    "puerperal_sepsis": "sepsis",
    "post_abortion_sepsis": "sepsis",
    "postoperative_infection": "sepsis",
    "other_sepsis": "sepsis",
    "obstructed_labor": "obstructed_rupture",
    "prolonged_labor": "obstructed_rupture",
    "uterine_rupture": "obstructed_rupture",
    "other_obstructed_rupture": "obstructed_rupture",
    "abortion_hemorrhage": "abortion",
    "unsafe_abortion": "abortion",
    "incomplete_abortion": "abortion",
    "other_abortion": "abortion",
    "pulmonary_embolism": "embolism",
    "amniotic_fluid_embolism": "embolism",
    "other_embolism": "embolism",
    "severe_anemia": "indirect",
    "cardiac_disease": "indirect",
    "respiratory_disease": "indirect",
    "liver_disease_pregnancy": "indirect",
    "renal_disease": "indirect",
    "malaria": "indirect",
    "tuberculosis": "indirect",
    "diabetes": "indirect",
    "other_indirect": "indirect",
    "unknown_under_investigation": "unknown",
    "other_specified": "other",
}

class Mpdsr(models.Model):
    yearmpdsr = models.IntegerField(
        default=2026, choices=YCHOICES, 
        verbose_name="Year")
    monthmpdsr = models.CharField(
        max_length=2,
        choices=MONTH_CHOICES,
        default="1",
        verbose_name="Month"
    )

    facilityname = models.ForeignKey(
        "hiva.Facility",
        on_delete=models.CASCADE,
        verbose_name="Health Facility Name"
    )

    n_mpdsrcommittee = models.IntegerField(
        default=0, verbose_name="Number HF staff who participated in the MPDSR Committee")
    n_maternaldeathreported = models.IntegerField(
        default=0, verbose_name="Number of Maternal Death reported")
    n_maternaldeathreviewed = models.IntegerField(
        default=0, verbose_name="Number of Maternal Death reviewed")
    causeofmaternaldeaths_m = models.TextField(
        max_length=200, blank=True, null=True, verbose_name="Cause of maternal deaths")
    nastillbirthreportedreported = models.IntegerField(
        default=0, verbose_name="Number of antepartum Still birth reported")
    nastillbirthreportedreviewed = models.IntegerField(
        default=0, verbose_name="Number of antepartum Still birth reviewed")
    nistillbirthreported = models.IntegerField(
        default=0, verbose_name="Number of intrapartum Still birth reported")
    nistillbirthreviewed = models.IntegerField(
        default=0, verbose_name="Number of intrapartum Still birth reviewed")
    nndeath_afteralivebirth_reported = models.IntegerField(
        default=0, verbose_name="Number of Neonatal Death (after a live birth) reported")
    nndeath_afteralivebirth_reviewed = models.IntegerField(
        default=0, verbose_name="Number of neonatal Death (after a live birth) reviewed")
    causeofneonataldeath_n = models.TextField(
        max_length=200, blank=True, null=True, verbose_name="Cause of neonatal death")
    interventionperformed = models.TextField(
        max_length=200, blank=True, null=True, verbose_name="Intervention performed")
    recfromMPDSRcommittee = models.TextField(
        max_length=500, blank=True, null=True, verbose_name="Recommendation from MPDSR committee")
    remarks = models.TextField(
        max_length=500, blank=True, null=True)

    maternal_death_cause_category = models.CharField(
        max_length=40,
        choices=MATERNAL_DEATH_CAUSE_CATEGORY_CHOICES,
        null=True,
        blank=True,
        verbose_name="Maternal death cause category",
        help_text="Structured category for new records. Leave blank if no maternal death reported."
    )

    maternal_death_specific_cause = models.CharField(
        max_length=50,
        choices=MATERNAL_DEATH_SPECIFIC_CAUSE_CHOICES,
        null=True,
        blank=True,
        verbose_name="Maternal death specific cause",
        help_text="Specific structured cause for new records. Leave blank if no maternal death reported."
    )

    maternal_death_contributing_factor = models.CharField(
        max_length=50,
        choices=MATERNAL_DEATH_CONTRIBUTING_FACTOR_CHOICES,
        null=True,
        blank=True,
        verbose_name="Maternal death contributing factor",
        help_text="Main contributing factor identified through no-blame MPDSR review."
    )

    maternal_death_preventability = models.CharField(
        max_length=30,
        choices=MATERNAL_DEATH_PREVENTABILITY_CHOICES,
        null=True,
        blank=True,
        verbose_name="Maternal death preventability"
    )

    maternal_death_timing = models.CharField(
        max_length=30,
        choices=MATERNAL_DEATH_TIMING_CHOICES,
        null=True,
        blank=True,
        verbose_name="Timing of maternal death"
    )

    maternal_death_place = models.CharField(
        max_length=30,
        choices=MATERNAL_DEATH_PLACE_CHOICES,
        null=True,
        blank=True,
        verbose_name="Place of maternal death"
    )

    # ✅ many users can create records; uniqueness is not by user
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mpdsr_created",
        editable=False
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,
        blank=True,
        editable=False
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mpdsr_updated",
        editable=False
    )
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        verbose_name = "MPDSR"
        verbose_name_plural = "MPDSR"
        ordering = ["-yearmpdsr", "-monthmpdsr", "facilityname"]
        constraints = [
            models.UniqueConstraint(
                fields=["facilityname", "yearmpdsr", "monthmpdsr"],
                name="uniq_facility_year_month_mpdsr"
            )
        ]

    def clean(self):
        super().clean()

        # Existing integrity checks
        if self.n_maternaldeathreviewed > self.n_maternaldeathreported:
            raise ValidationError({
                "n_maternaldeathreviewed": "Reviewed cannot be greater than reported."
            })

        if self.nndeath_afteralivebirth_reviewed > self.nndeath_afteralivebirth_reported:
            raise ValidationError({
                "nndeath_afteralivebirth_reviewed": "Reviewed cannot be greater than reported."
            })

        if self.nastillbirthreportedreviewed > self.nastillbirthreportedreported:
            raise ValidationError({
                "nastillbirthreportedreviewed": "Reviewed cannot be greater than reported."
            })

        if self.nistillbirthreviewed > self.nistillbirthreported:
            raise ValidationError({
                "nistillbirthreviewed": "Reviewed cannot be greater than reported."
            })

        deaths_reported = self.n_maternaldeathreported or 0

        # New structured-field validation
        # These checks only apply to the NEW optional fields and do not disturb legacy data
        structured_fields_used = any([
            self.maternal_death_cause_category,
            self.maternal_death_specific_cause,
            self.maternal_death_contributing_factor,
            self.maternal_death_preventability,
            self.maternal_death_timing,
            self.maternal_death_place,
        ])

        if deaths_reported == 0 and structured_fields_used:
            errors = {}
            if self.maternal_death_cause_category:
                errors["maternal_death_cause_category"] = "Leave blank when no maternal death is reported."
            if self.maternal_death_specific_cause:
                errors["maternal_death_specific_cause"] = "Leave blank when no maternal death is reported."
            if self.maternal_death_contributing_factor:
                errors["maternal_death_contributing_factor"] = "Leave blank when no maternal death is reported."
            if self.maternal_death_preventability:
                errors["maternal_death_preventability"] = "Leave blank when no maternal death is reported."
            if self.maternal_death_timing:
                errors["maternal_death_timing"] = "Leave blank when no maternal death is reported."
            if self.maternal_death_place:
                errors["maternal_death_place"] = "Leave blank when no maternal death is reported."
            if errors:
                raise ValidationError(errors)

        if deaths_reported > 0:
            # Only require category/specific cause if user starts using the new structured fields
            if self.maternal_death_specific_cause and not self.maternal_death_cause_category:
                raise ValidationError({
                    "maternal_death_cause_category": "Please select the maternal death cause category."
                })

            if self.maternal_death_cause_category and not self.maternal_death_specific_cause:
                raise ValidationError({
                    "maternal_death_specific_cause": "Please select the maternal death specific cause."
                })

        if self.maternal_death_specific_cause and self.maternal_death_cause_category:
            expected_category = SPECIFIC_CAUSE_CATEGORY_MAP.get(self.maternal_death_specific_cause)
            if expected_category and expected_category != self.maternal_death_cause_category:
                raise ValidationError({
                    "maternal_death_specific_cause": "Selected specific cause does not match the selected category."
                })

    def __str__(self):
        return f"{self.facilityname} - {self.yearmpdsr}/{int(self.monthmpdsr):02d}"
    
class aimpee(models.Model):
    shamsimonth = models.CharField()
    shamsiyear = models.CharField()
    period = models.CharField()
    bl_progress = models.CharField()
    aimfacilityname = models.ForeignKey(Facility, 
    on_delete=models.CASCADE, verbose_name="Health Facility Name")
    gre_month =models.CharField()
    gre_year= models.CharField()
    afiat_flag = models.BooleanField()

     # =========================
    # ANC / OPD – Screening
    # =========================
    anc_total_seen = models.BigIntegerField(
        default=0,
        verbose_name="1. Number of pregnant women seen in ANC"
    )

    anc_bp_measured = models.BigIntegerField(
        default=0,
        verbose_name="2. Number of ANC women with blood pressure measured"
    )

    preeclampsia_diagnosed = models.BigIntegerField(
        default=0,
        verbose_name="3. Number of ANC women diagnosed with Pre-Eclampsia (BP >140/90 + proteinuria)"
    )

    # =========================
    # Severe Pre-E / Eclampsia
    # =========================
    severe_pree_or_eclampsia = models.BigIntegerField(
        default=0,
        verbose_name="4. Number of patients with Severe Pre-Eclampsia or Eclampsia WITH BP > 160 Systolic OR 110 diastolic"
    )

    severe_pree_antihypertensive_within_1hr = models.BigIntegerField(
        default=0,
        verbose_name="5. Number of patients with Severe Pre-eclampsia or Eclampsia WITH BP > 160 Systolic OR 110 diastolic who received an antihypertensive medication within one hour of the diagnosis"
    )

    # =========================
    # OPD / ANC Follow-up
    # =========================
    opd_pree_seen_by_md = models.BigIntegerField(
        default=0,
        verbose_name="6. Number of outpatients diagnosed in OPD with Pre-Eclampsia by MD(AAC member must check that the patient with high BP is seen by the MD in OPD)"
    )

    opd_pree_twice_weekly_followup = models.BigIntegerField(
        default=0,
        verbose_name="7. Number of outpatients seen in ANC/OPD ward with Pre-Eclampsia who returned to ANC/OPD ward twice a week"
    )

    opd_pree_weekly_lab_testing = models.BigIntegerField(
        default=0,
        verbose_name="8. Number of outpatients seen in ANC/OPD ward with Pre-Eclampsia who received weekly laboratory testing"
    )

    opd_pree_weekly_lab_testing_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="9. Percentage of outpatients seen in ANC/OPD with Pre-Eclampsia who received weekly laboratory testing"
    )

    # =========================
    # Admission & Case Severity
    # =========================
    pree_admitted_from_anc = models.BigIntegerField(
        default=0,
        verbose_name="10. Number of Patients with Pre-E diagnosed in ANC clinic who required admision (Admitted patients)"
    )

    spe_admissions_before_delivery = models.BigIntegerField(
        default=0,
        verbose_name="11. Number of patients admitted to HFs with SEVERE PRE-ECLAMPSIA (SPE) before delivery, birth (including referrals in)"
    )

    eclampsia_admissions_before_delivery = models.BigIntegerField(
        default=0,
        verbose_name="12. Number of patients admitted to a HFs with  Eclampsia before delivery, birth (including referrals in)"
    )

    magnesium_sulfate_within_1hr = models.BigIntegerField(
        default=0,
        verbose_name="13. Number of patients WITH SEVERE PRE-ECLAMPSIA or Eclampsia who received Magnesium Sulfate within one hour of the diagnosis"
    )

    # =========================
    # Hypertension Types
    # =========================
    chronic_htn_superimposed_pree = models.BigIntegerField(
        default=0,
        verbose_name="14. Number of patients with chronic hypertension* with superimposed pre-eclampsia"
    )

    gestational_hypertension = models.BigIntegerField(
        default=0,
        verbose_name="15. Number of patients with Gestational hypertension*"
    )

    # =========================
    # Delivery Timeliness
    # =========================
    spe_delivered_within_24hrs = models.BigIntegerField(
        default=0,
        verbose_name="16. Number of Severe Pre-eclampsia patients who delivered within 24 hours of admission"
    )

    eclampsia_delivered_within_12hrs = models.BigIntegerField(
        default=0,
        verbose_name="17. Number of Eclampsia patients who delivered within 12 hours of admission"
    )

    # =========================
    # Postpartum Follow-up
    # =========================
    post_delivery_followup_3days = models.BigIntegerField(
        default=0,
        verbose_name="18. Number of patients with SPE or eclampsia who had a follow up visit within 3 days after the delivery discharge"
    )

    postpartum_pree_eclampsia = models.BigIntegerField(
        default=0,
        verbose_name="19. Number of patients with SPE or eclampsia diagnosed during the post-partum period"
    )

    # =========================
    # Complications
    # =========================
    renal_failure = models.BigIntegerField(default=0, verbose_name="20. Renal Failure (LESS THAN 30 ml/hr for 4 hours despite fluid challenge)")
    pulmonary_edema = models.BigIntegerField(default=0, verbose_name="21. Pulmonary edema")
    eclamptic_seizure = models.BigIntegerField(default=0, verbose_name="22. Eclamptic seizure")
    stroke = models.BigIntegerField(default=0, verbose_name="23. Stroke (Cerebral Hemorrhage or Blood clot in brain)")
    thrombocytopenia = models.BigIntegerField(default=0, verbose_name="24. Thrombocytopenia (non-HELLP)")
    hellp_syndrome = models.BigIntegerField(default=0, verbose_name="25. HELLP syndrome")
    pres = models.BigIntegerField(default=0, verbose_name="26. PRES (Posterior Reversible Encephalopathy Syndrome)")
    intrauterine_fetal_death = models.BigIntegerField(default=0, verbose_name="27. Intrauterine fetal death")
    placental_abruption = models.BigIntegerField(default=0, verbose_name="28. Placental abruption")
    eclamptic_coma = models.BigIntegerField(default=0, verbose_name="29. Eclamptic coma")

    total_complications = models.BigIntegerField(
        default=0,
        verbose_name="30. Total complications due to SPE and Eclampsia"
    )

    maternal_death = models.BigIntegerField(
        default=0,
        verbose_name="31. Maternal deaths due to SPE or Eclampsia"
    )

    status = models.CharField(
    max_length=20,
    choices=[("draft","Draft"), ("submitted","Submitted")],
    default="draft"
)

    class Meta:
        verbose_name = "AIM-PEE"
        verbose_name_plural = "AIM-PEE"

    def __str__(self):
        return f"AIM-PEE Indicators #{self.id}"
    
class aimpph(models.Model):
    shamsimonth = models.CharField(verbose_name="Afghanistan Month")
    shamsiyear = models.CharField(verbose_name="Afghanistan Year")
    period = models.CharField(verbose_name="Period")
    bl_progress = models.CharField(verbose_name="Baseline and Progress")
    aimfacilityname = models.ForeignKey(Facility, on_delete=models.CASCADE, verbose_name="Health Facility Name")
    gre_month =models.CharField(verbose_name="Calender Month")
    gre_year= models.CharField(verbose_name="Calender Year")
    afiat_flag = models.BooleanField(verbose_name="AFIAT")

    # Births and oxytocin
    total_births = models.BigIntegerField(
        default=0,
        verbose_name="1. Number of ALL births (log book)"
    )
    births_vaginal = models.BigIntegerField(
        default=0,
        verbose_name="2. Number of births - by vaginal delivery"
    )
    births_csection = models.BigIntegerField(
        default=0,
        verbose_name="3. Number of births - by C-sections"
    )
    oxytocin_immediate = models.BigIntegerField(
        default=0,
        verbose_name="4. Number of patients receiving oxytocin immediately after birth"
    )
    antepartum_hemorrhage = models.BigIntegerField(
        default=0,
        verbose_name="5. Number of Antepartum Hemorrhage (Abruption, Placenta Previa)"
    )

    # PPH by mode of delivery / referrals
    pph_vaginal_501_999 = models.BigIntegerField(
        default=0,
        verbose_name="6. Number of Postpartum Hemorrhage (PPH) - after vaginal delivery (501–999 cc)"
    )
    pph_cs_1000_plus = models.BigIntegerField(
        default=0,
        verbose_name="7. Number of Postpartum Hemorrhage (PPH) - after Cesarean delivery (≥1000 cc)"
    )
    pph_referral_in_outside_aim = models.BigIntegerField(
        default=0,
        verbose_name="8. Number of Postpartum Hemorrhage (PPH) referrals in from outside of AIM facilities"
    )
    pph_referral_in_aim = models.BigIntegerField(
        default=0,
        verbose_name="9. Number of Postpartum Hemorrhage (PPH) referrals in from AIM facilities"
    )

    # ✅ NEW: Total PPH (as requested)
    pph_total = models.BigIntegerField(
        default=0,
        verbose_name="10. Total number of PPH cases (sum of indicators 6–9)"
    )

    # QBL (quantitative blood loss) categories
    qbl_0_500 = models.BigIntegerField(
        default=0,
        verbose_name="0–500 ml (Normal blood loss, NO PPH)"
    )
    qbl_501_999 = models.BigIntegerField(
        default=0,
        verbose_name="501–999 ml"
    )
    qbl_1000_1499 = models.BigIntegerField(
        default=0,
        verbose_name="1000–1499 ml"
    )
    qbl_1500_1999 = models.BigIntegerField(
        default=0,
        verbose_name="1500–1999 ml"
    )
    qbl_2000_2499 = models.BigIntegerField(
        default=0,
        verbose_name="2000–2499 ml"
    )
    qbl_2500_plus = models.BigIntegerField(
        default=0,
        verbose_name="> 2500 ml"
    )
    qbl_unknown = models.BigIntegerField(
        default=0,
        verbose_name="Unknown (estimated blood loss not recorded)"
    )
    qbl_total = models.BigIntegerField(
        default=0,
        verbose_name="QBL total"
    )

    # Transfers and maternal deaths
    transfers_out_pph = models.BigIntegerField(
        default=0,
        verbose_name="Number of patients transferred out from HF for PPH"
    )
    maternal_death_pph_transfer = models.BigIntegerField(
        default=0,
        verbose_name="Number of maternal deaths (transfers) due to PPH"
    )
    maternal_death_other_transfer = models.BigIntegerField(
        default=0,
        verbose_name="Number of maternal deaths (transfers) due to other causes"
    )
    maternal_death_total_transfer = models.BigIntegerField(
        default=0,
        verbose_name="Total number of maternal deaths (transfers) – PPH and other causes"
    )

    # Causes of PPH
    cause_uterine_atony = models.BigIntegerField(
        default=0,
        verbose_name="Uterine atony"
    )
    cause_severe_lacerations = models.BigIntegerField(
        default=0,
        verbose_name="Severe vaginal or cervical lacerations which contributed to the PPH"
    )
    cause_retained_products = models.BigIntegerField(
        default=0,
        verbose_name="Retained products of conception (total or partial retention of placenta)"
    )
    cause_dic = models.BigIntegerField(
        default=0,
        verbose_name="DIC (coagulopathy)"
    )
    cause_ruptured_uterus = models.BigIntegerField(
        default=0,
        verbose_name="Ruptured uterus"
    )
    cause_abruption = models.BigIntegerField(
        default=0,
        verbose_name="Abruption placenta"
    )
    cause_placenta_previa = models.BigIntegerField(
        default=0,
        verbose_name="Placenta previa"
    )
    cause_placenta_accreta = models.BigIntegerField(
        default=0,
        verbose_name="Placenta accreta"
    )
    cause_other = models.BigIntegerField(
        default=0,
        verbose_name="Other causes of PPH"
    )
    cause_unknown = models.BigIntegerField(
        default=0,
        verbose_name="Unknown cause of PPH"
    )
    causes_total = models.BigIntegerField(
        default=0,
        verbose_name="TOTAL causes of PPH (may be more than 100%)"
    )

    # ✅ NEW: PPH management by medication (uterotonic)
    pph_medication_uterotonic = models.BigIntegerField(
        default=0,
        verbose_name="PPH management by medication (uterotonic)"
    )

    # Advanced interventions for PPH
    ai_uterine_compression = models.BigIntegerField(
        default=0,
        verbose_name="Uterine compression"
    )
    ai_manual_placenta = models.BigIntegerField(
        default=0,
        verbose_name="Manual removal of placenta"
    )
    ai_aortic_compression = models.BigIntegerField(
        default=0,
        verbose_name="Aortic compression"
    )
    ai_ubt = models.BigIntegerField(
        default=0,
        verbose_name="UBT (condom catheter)"
    )
    ai_lac_repair = models.BigIntegerField(
        default=0,
        verbose_name="Repair of severe vaginal or cervical lacerations causing a PPH"
    )
    ai_blynch_ual = models.BigIntegerField(
        default=0,
        verbose_name="B-Lynch suture or uterine artery ligation"
    )
    ai_nasg = models.BigIntegerField(
        default=0,
        verbose_name="Anti-shock garment (NASG)"
    )
    ai_ruptured_uterus_repair = models.BigIntegerField(
        default=0,
        verbose_name="Repair ruptured uterus"
    )
    ai_pph_hysterectomy = models.BigIntegerField(
        default=0,
        verbose_name="Postpartum hysterectomy for hemorrhage"
    )
    ai_hysterectomy_other = models.BigIntegerField(
        default=0,
        verbose_name="Postpartum hysterectomy (other causes)"
    )
    ai_total = models.BigIntegerField(
        default=0,
        verbose_name="Total number of advanced interventions conducted"
    )

    status = models.CharField(
    max_length=20,
    choices=[("draft","Draft"), ("submitted","Submitted")],
    default="draft")

    class Meta:
        verbose_name = "AIM-PPH"
        verbose_name_plural = "AIM-PPH"

    def __str__(self):
        return f"AIM-PPH #{self.id}"
    
class WhoChildbirthChecklistMonthly(models.Model):

    shamsi_month = models.CharField(verbose_name="Afghanistan Month")
    shamsi_year = models.CharField(verbose_name="Afghanistan Year")
    period = models.CharField(verbose_name="Period")
    bl_progress = models.CharField(verbose_name="Baseline and Progress")
    facility_name = models.ForeignKey(Facility, on_delete=models.CASCADE, verbose_name="Health Facility Name")
    gre_month =models.CharField(verbose_name="Calender Month")
    gre_year= models.CharField(verbose_name="Calender Year")
    afiat_flag = models.BooleanField(verbose_name="AFIAT")

    """
    WHO Childbirth Checklist – Monthly Facility Summary
    (Counts + auto-calculated ratios)
    """

    # --- 1) Deliveries (denominator for many indicators) ---
    total_deliveries = models.PositiveIntegerField(
        default=0,
        verbose_name="Total number of Deliveries (normal/assisted/c-sections)",
    )

    # --- 2) Sample size: randomly selected files (up to 20) ---
    files_selected = models.PositiveIntegerField(
        default=0,
        verbose_name=(
            "Out of total number of deliveries in the month, select RANDOMLY up to 20 patient files "
            "and record number of files selected"
        ),
        help_text="Expected range: 0–20.",
    )

    # --- Section 1 ---
    sec1_complete = models.PositiveIntegerField(
        default=0,
        verbose_name="Number of section 1 of the WHO childbirth Checklists completely filled out",
    )

    # --- Partograph at admission cervix ≥4 cm (from selected files) ---
    cervix_ge4_admission = models.PositiveIntegerField(
        default=0,
        verbose_name=(
            "Number of patient files selected with pregnant women presenting cervix ≥4 cms at admission"
        ),
    )
    partograph_started_ge4 = models.PositiveIntegerField(
        default=0,
        verbose_name="Number of partographs started at cervix ≥4 cms at admission",
    )

    # --- Section 2 ---
    sec2_complete = models.PositiveIntegerField(
        default=0,
        verbose_name="Number of section 2 of the WHO childbirth Checklists completely filled out",
    )

    # --- Newborn essential supplies at bedside (from deliveries) ---
    newborn_supplies_5_available = models.PositiveIntegerField(
        default=0,
        verbose_name="Number of deliveries with the 5 essential supplies available at bedside for newborn",
    )

    # --- Section 3 ---
    sec3_complete = models.PositiveIntegerField(
        default=0,
        verbose_name="Number of section 3 of the WHO childbirth Checklists completely filled out",
    )

    # --- Early breastfeeding + skin-to-skin (from deliveries) ---
    bf_s2s_first_hour = models.PositiveIntegerField(
        default=0,
        verbose_name=(
            "Number of deliveries which started breastfeeding and skin-to-skin contact during first hour "
            "(if mother and baby are well)."
        ),
    )

    # --- Section 4 ---
    sec4_complete = models.PositiveIntegerField(
        default=0,
        verbose_name="Number of section 4 of the WHO childbirth Checklists completely filled out",
    )

    # --- Antibiotic need checked before discharge (from deliveries) ---
    abx_need_checked_newborn = models.PositiveIntegerField(
        default=0,
        verbose_name=(
            "Number of deliveries for which the need for antibiotic for newborn was checked before discharge"
        ),
    )

    # --- All 4 sections complete (from selected files) ---
    all4_sections_complete = models.PositiveIntegerField(
        default=0,
        verbose_name="Number of patient files with the 4 sections of the WHO childbirth Checklists completely filled out",
    )

    # ---- Audit fields ----
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "WHO CHILDBIRTH CHECKLIST"
        verbose_name_plural = "WHO CHILDBIRTH CHECKLIST"
        unique_together = ("facility_name", "shamsi_year", "shamsi_month")
        ordering = ("-shamsi_year", "-shamsi_month", "facility_name")

    def __str__(self):
        return f"{self.facility_name} - {self.shamsi_year}/{self.shamsi_month}"

    # -----------------------------
    # Safe ratio helpers + metrics
    # -----------------------------
    @staticmethod
    def _ratio(numerator: int, denominator: int) -> float:
        if not denominator:
            return 0.0
        return round((numerator / denominator) * 100.0, 2)

    @property
    def sec1_completeness_ratio(self) -> float:
        # Indicator 4: Completeness ratio of section 1 (out of selected files)
        return self._ratio(self.sec1_complete, self.files_selected)

    @property
    def sec2_completeness_ratio(self) -> float:
        # Indicator 9: completeness rate of section 2 (out of selected files)
        return self._ratio(self.sec2_complete, self.files_selected)

    @property
    def sec3_completeness_ratio(self) -> float:
        # Indicator 13: completeness rate of section 3 (out of selected files)
        return self._ratio(self.sec3_complete, self.files_selected)

    @property
    def sec4_completeness_ratio(self) -> float:
        # completeness rate of section 4 (out of selected files)
        return self._ratio(self.sec4_complete, self.files_selected)

    @property
    def partograph_use_ge4_rate(self) -> float:
        # Indicator 7: partograph use at cervix ≥4 cm rate (out of cervix≥4 admissions)
        return self._ratio(self.partograph_started_ge4, self.cervix_ge4_admission)

    @property
    def newborn_supplies_5_ratio(self) -> float:
        # Indicator 11: ratio of deliveries with 5 essential supplies available (out of total deliveries)
        return self._ratio(self.newborn_supplies_5_available, self.total_deliveries)

    @property
    def bf_s2s_first_hour_ratio(self) -> float:
        # Indicator 19: ratio of deliveries started breastfeeding & skin-to-skin in first hour (out of total deliveries)
        return self._ratio(self.bf_s2s_first_hour, self.total_deliveries)

    @property
    def abx_need_checked_ratio(self) -> float:
        # Indicator 21: ratio of deliveries with newborn antibiotic need checked (out of total deliveries)
        return self._ratio(self.abx_need_checked_newborn, self.total_deliveries)

    @property
    def all4_sections_completeness_ratio(self) -> float:
        # completeness ratio of all 4 sections (out of selected files)
        return self._ratio(self.all4_sections_complete, self.files_selected)

    def clean(self):
        """
        Light validation to avoid impossible values.
        (Admin/form will show user-friendly errors.)
        """
        errors = {}

        if self.files_selected > 20:
            errors["files_selected"] = "files_selected must be 0–20 (random sample up to 20)."

        # Counts based on selected files should not exceed files_selected
        for field in ["sec1_complete", "sec2_complete", "sec3_complete", "sec4_complete", "all4_sections_complete"]:
            if getattr(self, field) > self.files_selected:
                errors[field] = f"{field} cannot be greater than files_selected."

        # Partograph denominators
        if self.cervix_ge4_admission > self.files_selected:
            errors["cervix_ge4_admission"] = "Cannot be greater than files_selected."
        if self.partograph_started_ge4 > self.cervix_ge4_admission:
            errors["partograph_started_ge4"] = "Cannot be greater than cervix_ge4_admission."

        # Delivery-based counts should not exceed total deliveries
        for field in ["newborn_supplies_5_available", "bf_s2s_first_hour", "abx_need_checked_newborn"]:
            if getattr(self, field) > self.total_deliveries:
                errors[field] = f"{field} cannot be greater than total_deliveries."

        if errors:
            from django.core.exceptions import ValidationError
            raise ValidationError(errors)

class safesurgeryclinical(models.Model):

    shamsimonth = models.CharField(verbose_name="Afghanistan Month")
    shamsiyear = models.CharField(verbose_name="Afghanistan Year")
    period = models.CharField(verbose_name="Period")
    bl_progress = models.CharField(verbose_name="Baseline and Progress")
    aimfacilityname = models.ForeignKey(Facility, on_delete=models.CASCADE, verbose_name="Health Facility Name")
    gre_month =models.CharField(verbose_name="Calender Month")
    gre_year= models.CharField(verbose_name="Calender Year")
    afiat_flag = models.BooleanField(verbose_name="AFIAT")

    # Core volumes
    total_cs = models.BigIntegerField(default=0,
        verbose_name="Total Number of Cesarean Section",
        null=True, blank=True
    )
    total_deliv = models.BigIntegerField(default=0,
        verbose_name="Total Number of Deliveries",
        null=True, blank=True
    )
    cs_rate = models.DecimalField(default=0,
        verbose_name="Cesarean Section Rate",
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        help_text="Percentage (%)"
    )

    # WHO Surgical Safety Checklist
    who_ssc_completed = models.BigIntegerField(default=0,
        verbose_name="Number of WHO Surgical Safety Checklists completed",
        null=True, blank=True
    )
    who_ssc_rate = models.DecimalField(default=0,
        verbose_name="Surgical Safety Checklist completion rate",
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        help_text="Percentage (%)"
    )

    # Safe Surgery Tracker
    safe_tracker_complete = models.BigIntegerField(default=0,
        verbose_name="Number of Safe Surgery Tracker with all fields completed",
        null=True, blank=True
    )
    safe_tracker_rate = models.DecimalField(default=0,
        verbose_name="Safe Surgery Tracker completion rate",
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        help_text="Percentage (%)"
    )

    # PPH during/after CS
    pph_cs_num = models.BigIntegerField(default=0,
        verbose_name="Number of Post-Partum Hemorrhage cases during or after CS",
        null=True, blank=True
    )
    pph_cs_rate = models.DecimalField(default=0,
        verbose_name="Cesarean PPH Rate (>500 ml)",
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        help_text="Percentage (%)"
    )

    # QBL
    qbl_cs_num = models.BigIntegerField(default=0,
        verbose_name="Number of C-Section cases with QBL performed & recorded",
        null=True, blank=True
    )
    qbl_cs_rate = models.DecimalField(default=0,
        verbose_name="QBL performance rate during C-sections",
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        help_text="Percentage (%)"
    )

    # Post-op fever
    postop_fever_num = models.BigIntegerField(default=0,
        verbose_name="Number of CS with post-operation fever (>38℃) requiring antibiotics",
        null=True, blank=True
    )
    postop_fever_rate = models.DecimalField(default=0,
        verbose_name="Post operation fever (>38℃) rate requiring antibiotics",
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        help_text="Percentage (%)"
    )

    # Injuries
    bladder_injury_num = models.BigIntegerField(default=0,
        verbose_name="Number of cases of injury to bladder due to CS",
        null=True, blank=True
    )
    bladder_injury_rate = models.DecimalField(default=0,
        verbose_name="Injury to bladder rate due to CS",
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        help_text="Percentage (%)"
    )

    bowel_injury_num = models.BigIntegerField(default=0,
        verbose_name="Number of injury to bowel due to CS",
        null=True, blank=True
    )
    bowel_injury_rate = models.DecimalField(default=0,
        verbose_name="Injury to bowel rate due to CS",
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        help_text="Percentage (%)"
    )

    # Hysterectomy
    hyst_num = models.BigIntegerField(default=0,
        verbose_name="Number of hysterectomy during or after CS",
        null=True, blank=True
    )
    hyst_rate = models.DecimalField(default=0,
        verbose_name="Hysterectomy rate during or after CS",
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        help_text="Percentage (%)"
    )

    # Vaginal cleansing
    vag_clean_num = models.BigIntegerField(default=0,
        verbose_name="Number of vaginal cleansing before CS",
        null=True, blank=True
    )
    vag_clean_rate = models.DecimalField(default=0,
        verbose_name="Vaginal cleansing rate",
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        help_text="Percentage (%)"
    )

    # Foley catheter
    foley_after_anes_num = models.BigIntegerField(default=0,
        verbose_name="Number of Foley catheter applied after induction of anesthesia",
        null=True, blank=True
    )
    foley_after_anes_rate = models.DecimalField(default=0,
        verbose_name="CS rate with Foley catheter after anesthesia induction",
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        help_text="Percentage (%)"
    )

    # Antibiotic prophylaxis
    abx_proph_num = models.BigIntegerField(default=0,
        verbose_name="Number of CS with IV prophylactic antibiotic provided prior to CS",
        null=True, blank=True
    )
    abx_proph_rate = models.DecimalField(default=0,
        verbose_name=(
            "Antibiotic prophylaxis rate (15–60 minutes prior to incision) – "
            "Cefazolin or other cephalosporin according to availability"
        ),
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        help_text="Percentage (%)"
    )

    # Incision skin prep
    skin_prep_num = models.BigIntegerField(default=0,
        verbose_name="Number of CS with incision skin preparation performed",
        null=True, blank=True
    )
    skin_prep_rate = models.DecimalField(default=0,
        verbose_name="Rate of incision site skin preparation",
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        help_text="Percentage (%)"
    )

    # Maternal deaths
    mat_death_pph_cs = models.BigIntegerField(default=0,
        verbose_name="Number of maternal deaths due to PPH related to CS",
        null=True, blank=True
    )
    mat_death_other_cs = models.BigIntegerField(default=0,
        verbose_name="Number of maternal deaths due to other causes related to CS",
        null=True, blank=True
    )
    mat_death_total = models.BigIntegerField(default=0,
        verbose_name="Total number of maternal deaths related or not to CS",
        null=True, blank=True
    )

    status = models.CharField(
    max_length=20,
    choices=[("draft","Draft"), ("submitted","Submitted"), ("approved","Approved")],
    default="draft")

    class Meta:
        verbose_name = "SAFE SURGERY"
        verbose_name_plural = "SAFE SURGERY"

    def __str__(self):
        return f"SAFE SURGERY #{self.pk or ''}"



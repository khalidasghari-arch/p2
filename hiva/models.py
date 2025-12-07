from django.db import models
# Create your models here.

class Province(models.Model):
    name = models.CharField(max_length=200)
    provinceshortname = models.CharField(max_length=200, null=True, blank=True)
    description = models.TextField(blank=True)
    provincecode = models.IntegerField(blank=True, null=True)
    province = models.CharField(blank=True, null=True)
    provinceDari = models.CharField(blank=True, null=True)
    provincePashto = models.CharField(blank=True, null=True)
    phase = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return self.name
    
class District(models.Model):
    provincefk = models.ForeignKey(Province, on_delete=models.CASCADE, default=1)
    name = models.TextField(max_length=200)
    description = models.TextField(blank=True)
    districtcode = models.IntegerField(blank=True, null=True)
    district = models.CharField(blank=True, null=True)
    districtdari = models.CharField(blank=True, null=True)
    districtpashto = models.CharField(blank=True, null=True)

    def __str__(self):
        return self.name

class Facilitytype(models.Model):
    name = models.CharField(max_length=200)
    shortname = models.TextField(blank=True)
    namedari = models.CharField(blank=True, null=True)
    namepashto = models.CharField(blank=True, null=True)

    def __str__(self):
        return self.name
    
class Facility(models.Model):
    districtfk = models.ForeignKey(District, on_delete=models.CASCADE, default=1, verbose_name='District')
    facilitytypefk = models.ForeignKey(Facilitytype, on_delete=models.CASCADE, default=1, verbose_name='Facility Type')
    name = models.TextField(max_length=200, verbose_name='Facility Name')
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
    skilllab = models.BooleanField(blank=True, default=False)
    aimphase = models.IntegerField(blank=True, null=True)  

    def __str__(self):
        return self.name

class Implementor(models.Model):
    name = models.CharField(max_length=200)
    shortname = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Assessor(models.Model):
    name = models.CharField(max_length=200)
    contact = models.TextField(blank=True)
    email = models.CharField(blank=True, null=True)
    tazkira = models.CharField(blank=True, null=True)
    gender = models.CharField(blank=True, null=True)
    implementer = models.ForeignKey(Implementor, on_delete=models.CASCADE, null=True, blank=True)
    province = models.ForeignKey(Province, on_delete=models.CASCADE, null=True, blank=True)
    Status = models.CharField(blank=True, null=True)
    phaseonecloseout = models.DateField(blank=True, null=True)
    continuetophase2 = models.BooleanField(blank=True, null=True)
    note = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Assessmenttype(models.Model):
    name = models.CharField(max_length=200)
    shortname = models.TextField(blank=True)

    def __str__(self):
        return self.name
    
class Area(models.Model):
    name = models.TextField(max_length=200)
    shortname = models.TextField(blank=True)

    def __str__(self):
        return self.name
    
class Section(models.Model):
    areafk = models.ForeignKey(Area, on_delete=models.CASCADE, null=True, blank=True)
    name = models.TextField()
    shortname = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Standards(models.Model):
    sectionfk = models.ForeignKey(Section, on_delete=models.CASCADE, null=True, blank=True)
    name = models.TextField()
    shortname = models.TextField(blank=True)

    def __str__(self):
        return self.name
    
class Score(models.Model):
    name = models.TextField()
    shorname = models.TextField(blank=True)

    def __str__(self):
        return self.name
     
class Criteria(models.Model):
    standardfk = models.ForeignKey(Standards, on_delete=models.CASCADE, null=True, blank=True)
    scorefk = models.ForeignKey(Score, on_delete=models.CASCADE)
    name = models.TextField()
    shortname = models.TextField(blank=True)
    namedari = models.TextField(blank=True)
    createdby = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name
    
class ThematicMentorship(models.Model):
    name = models.CharField()
    shortname = models.CharField

    def __str__(self):
        return self.name
    
class MentorshipTopics(models.Model):
    thematicfk = models.ForeignKey(ThematicMentorship, on_delete=models.CASCADE, null=True, blank=True)
    shortname = models.CharField(null=True, blank=True)
    name = models.TextField()
    namedari = models.TextField(null=True, blank=True)
    namepashto = models.TextField(null=True, blank=True)
    nameeng= models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

class Mentorshipvisit(models.Model):
    facilityfk = models.ForeignKey(Facility, on_delete=models.CASCADE)
    visitdate = models.DateField()
    visitround = models.IntegerField(null=True, blank=True)
    mentorshipstarttime = models.TimeField()
    mentorshipendtime = models.TimeField()

    def __str__(self):
        return f"Mentorship Visit Date {self.visitdate}"
    
class Position(models.Model):
    name = models.CharField()

    def __str__(self):
        return self.name

class Staff(models.Model):
    hfname = models.ForeignKey(Facility, on_delete=models.CASCADE)
    firstname = models.CharField()
    lastname = models.CharField(blank=True, null=True)
    position = models.ForeignKey(Position, on_delete=models.CASCADE)
    tazkiranumber = models.CharField(blank=True, null=True)
    gender = models.CharField()
    status = models.CharField()

    def __str__(self):
        return self.firstname

class Mentorshipdetails(models.Model):
    mentorshipvistfk = models.ForeignKey(Mentorshipvisit, on_delete=models.CASCADE, related_name="items", null=True, blank=True)
    menteename = models.ForeignKey(Staff, on_delete=models.CASCADE, null=True, blank=True)
    thematicname = models.ForeignKey(ThematicMentorship, on_delete=models.CASCADE, null=True, blank=True) 
    topicname = models.ForeignKey(MentorshipTopics, on_delete=models.CASCADE, null=True, blank=True, verbose_name="shortname") 
    mentor = models.ForeignKey(Assessor, on_delete=models.CASCADE, null=True, blank=True)
    ls = models.BooleanField()
    pc = models.BooleanField()
    mc = models.BooleanField()
    image = models.ImageField(upload_to='images/', null=True, blank=True)  # Files are stored in the media directory by default
    uploaded_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __int__(self):
        return self.id

class Assessment(models.Model):
    areafk = models.ForeignKey(Area, on_delete=models.CASCADE)
    sectionfk = models.ForeignKey(Section, on_delete=models.CASCADE)
    standardfk = models.ForeignKey(Standards, on_delete=models.CASCADE)
    criteriafk = models.ForeignKey(Criteria, on_delete=models.CASCADE)
    scorefk = models.ForeignKey(Score, on_delete=models.CASCADE)
    assesorfk = models.ForeignKey(Assessor, on_delete=models.CASCADE)
    facilityfk = models.ForeignKey(Facility, on_delete=models.CASCADE)
    implementorfk = models.ForeignKey(Implementor, on_delete=models.CASCADE)
    assessmenttype = models.ForeignKey(Assessmenttype, on_delete=models.CASCADE)
    assessmentdate = models.DateField()
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.remarks
    
class Participationtype(models.Model):
    name = models.TextField()

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

    def __str__(self):
        return self.trainingname

class Participanteducation(models.Model):
    name = models.TextField()
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name
    
class Participantposition(models.Model):
    name = models.TextField()
    remarks = models.TextField(blank=True, null=True)

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

    def __str__(self):
        return self.firstname
    
class ProjectGoal(models.Model):
    name = models.TextField()

    def __str__(self):
        return self.name
    
class ProjectObjective(models.Model):
    ProjectGoal = models.ForeignKey(ProjectGoal, on_delete=models.CASCADE)
    name = models.TextField()

    def __str__(self):
        return self.name

class ProjectOutput(models.Model):
    ProjectObjective = models.ForeignKey(ProjectObjective, on_delete=models.CASCADE)
    name = models.TextField()

    def __str__(self):
        return self.name
    
class IndicatorType(models.Model):
    name = models.TextField()

    def __str__(self):
        return self.name
    
class Indicator(models.Model):
    indicatortype = models.ForeignKey(IndicatorType, on_delete=models.CASCADE)
    indicatoroutput = models.ForeignKey(ProjectObjective, on_delete=models.CASCADE)
    name = models.TextField()
    datasource = models.TextField()
    baseline = models.CharField(max_length=200)
    target = models.CharField(max_length=200)
    achivement = models.CharField()
    indicatormodality = models.CharField(blank=True, null=True)
    remarks = models.CharField(max_length=200)

    def __str__(self):
        return self.name

class Qqmdomain(models.Model):
    name = models.TextField()
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class QqmdomainIndicator(models.Model):
    domain = models.ForeignKey(Qqmdomain, on_delete=models.CASCADE, blank=True, null=True)
    name = models.TextField(blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name
    
class tpm(models.Model):
    auditdate = models.DateField(blank=True, null=True)
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, blank=True, null=True)
    domainindicator = models.ForeignKey(QqmdomainIndicator, on_delete=models.CASCADE, blank=True, null=True)
    score = models.DecimalField(max_digits = 5, decimal_places = 2, null=True)
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"TPM Date {self.auditdate}"
    
class Qiccriterialist(models.Model):
    qiccriteriadate = models.DateField()
    qiccriterianame = models.CharField(max_length=200)
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Criteria Date {self.qiccriteriadate}"
    
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

    def __str__(self):
        return f"{self.qicfacility} {self.qiccommdate}" 
    
class Mpdsr(models.Model):
    yearmpdsr = models.IntegerField(default=2025, verbose_name="Year")
    monthmpdsr = models.CharField(max_length=200, default="January", verbose_name="Month" )
    facilityname = models.ForeignKey(Facility, on_delete=models.CASCADE, verbose_name="Health Facility Name")
    n_mpdsrcommittee = models.IntegerField(default=0, verbose_name="Number HF staff who participated in the MPDSR Committee")
    n_maternaldeathreported = models.IntegerField(default=0, verbose_name="Number of Maternal Death reported")
    n_maternaldeathreviewed = models.IntegerField(default=0, verbose_name="Number of Maternal Death reviewed")
    causeofmaternaldeaths_m = models.CharField(max_length=200, verbose_name="Cause of maternal deaths")
    nastillbirthreportedreported = models.IntegerField(default=0, verbose_name="Number of antepartum Still birth reported")
    nastillbirthreportedreviewed = models.IntegerField(default=0, verbose_name="Number of antepartum Still birth reviewed")
    nistillbirthreported = models.IntegerField(default=0, verbose_name="Number of intrapartum Still birth reported")
    nistillbirthreviewed = models.IntegerField(default=0, verbose_name="Number of intrapartum Still birth reviewed")
    nndeath_afteralivebirth_reported = models.IntegerField(default=0, verbose_name="Number of Neonatal Death (after a live birth) reported")
    nndeath_afteralivebirth_reviewed = models.IntegerField(default=0, verbose_name="Number of neonatal Death (after a live birth) reviewed")
    causeofneonataldeath_n = models.CharField(max_length=200, verbose_name="Cause of neonatal death")
    interventionperformed  = models.CharField(max_length=200, verbose_name="Intervention performed")
    recfromMPDSRcommittee = models.CharField(max_length=500, verbose_name="Recommendation from MPDSR committee")
    remarks = models.TextField(blank=True, null=True)
    image = models.FileField(upload_to='mpdsr-docs/', null=True, blank=True)  # Files are stored in the media directory by default
    uploaded_at = models.DateField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return f"{self.facilityname} {self.monthmpdsr}" 
    
class Gancohort(models.Model):
    facilityname = models.ForeignKey(Facility, on_delete=models.CASCADE, verbose_name="Health Facility Name")
    cohortname = models.TextField()
    cohortnumber = models.IntegerField()
    cohortstatus = models.TextField()
    cohortchecklist = models.TextField()
    cohortcreatedby = models.TextField()
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.cohortname
    
class Gancenrollment(models.Model):
    cohortname = models.ForeignKey(Gancohort, on_delete=models.CASCADE, verbose_name="Cohort Name")
    enrollmentid= models.IntegerField(blank=True, null=True)
    name = models.TextField()
    fathername = models.TextField()
    contactnumber = models.TextField()
    address = models.TextField()
    gafirstanc = models.IntegerField()
    edd = models.DateField()
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name
    
class Gancfirstsession(models.Model):
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
    clabexm = models.TextField(verbose_name="Completing Laboratory Exam (Y/N)")
    hemoglobin = models.TextField(verbose_name="Hemoglobin")
    urinexam = models.TextField(verbose_name="Urine exam/Protein Uria (NO/+,++,+++)")
    rpositivepuriatomd = models.TextField(verbose_name="Referred  Positive Protin Uria to MD (Y/N)")
    coughmorethantwoweeks= models.TextField(verbose_name="cough for more than two weeks(Y/N)")
    rcough = models.TextField(verbose_name="Referred cough for more than two week to DOTS Room")
    ttvaccine = models.TextField(verbose_name="TT vaccine (Y/N)")
    dangersign = models.TextField(verbose_name="Danger signs during pregnancy (Y/N) ")
    typeofdangersign = models.TextField(verbose_name="Type of Danger sign")
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.sessiontype
    
class Gancsecondsession(models.Model):
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
    mebendazole = models.TextField(verbose_name="Mebendazole (Y/N)") 
    muac = models.TextField(verbose_name="MUAC")
    dmam = models.TextField(verbose_name="Diagnosed with MAM (Y/N)")
    rmam = models.TextField(verbose_name="Refer MAM to Nutrition Counsellor (Y/N))")
    dsam = models.TextField(verbose_name="Diagnosed with SAM (Y/N)")
    rsam = models.TextField(verbose_name="Refer SAM to higher level (Y/N)")
    urinexam = models.TextField(verbose_name="Urine exam/Protein Uria (NO/+,++,+++)")
    rpositivepuriatomd = models.TextField(verbose_name="Referred  Positive Protin Uria to MD (Y/N)")
    coughmorethantwoweeks= models.TextField(verbose_name="cough for more than two weeks(Y/N)")
    rcough = models.TextField(verbose_name="Referred cough for more than two week to DOTS Room")
    ttvaccine = models.TextField(verbose_name="TT vaccine (Y/N)")
    dangersign = models.TextField(verbose_name="Danger signs during pregnancy (Y/N) ")
    typeofdangersign = models.TextField(verbose_name="Type of Danger sign")   
    remarks = models.TextField(blank=True, null=True)

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

    def __str__(self):
        return self.sessiontype
    
class SkillLabtracker(models.Model):
    hfname = models.ForeignKey(Facility, on_delete=models.CASCADE)
    skilllabname = models.CharField()
    skilllabstatus = models.CharField()
    skilllabround = models.IntegerField()
    skilllabdate = models.DateField()
    skilllabcheckin = models.TimeField()
    skilllabcheckout = models.TimeField()
    skilllabmenteename = models.ForeignKey(Staff, on_delete=models.CASCADE)
    thematicname = models.ForeignKey(ThematicMentorship, on_delete=models.CASCADE) 
    topicname = models.ForeignKey(MentorshipTopics, on_delete=models.CASCADE) 
    mentor = models.ForeignKey(Assessor, on_delete=models.CASCADE)
    ls = models.BooleanField()
    mc = models.BooleanField()
    mentororg = models.CharField()
    ce_checklist_applied = models.BooleanField()

    def __str__(self):
        return f"{self.skilllabdate} {self.skilllabname}" 
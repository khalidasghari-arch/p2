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

    class Meta:
        verbose_name = "PROVINCE"
        verbose_name_plural = "PROVINCE"

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

    class Meta:
        verbose_name = "DISTRICT"
        verbose_name_plural = "DISTRICT"

    def __str__(self):
        return self.name

class Facilitytype(models.Model):
    name = models.CharField(max_length=200)
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

    class Meta:
        verbose_name = "HEALTH FACILITY"
        verbose_name_plural = "HEALTH FACILITY"  

    def __str__(self):
        return self.name

class Implementor(models.Model):
    name = models.CharField(max_length=200)
    shortname = models.TextField(blank=True)

    class Meta:
        verbose_name = "IMPLEMENTER"
        verbose_name_plural = "IMPLEMENTER"

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

    class Meta:
        verbose_name = "CLINICAL MENTOR"
        verbose_name_plural = "CLINICAL MENTOR"

    def __str__(self):
        return self.name

class Assessmenttype(models.Model):
    name = models.CharField(max_length=200)
    shortname = models.TextField(blank=True)

    class Meta:
        verbose_name = "ASSESSMENT TYPE"
        verbose_name_plural = "ASSESSMENT TYPE"

    def __str__(self):
        return self.name
    
class Area(models.Model):
    name = models.TextField(max_length=200)
    shortname = models.TextField(blank=True)

    class Meta:
        verbose_name = "THEMATIC AREA"
        verbose_name_plural = "THEMATIC AREA"

    def __str__(self):
        return self.name
    
class Section(models.Model):
    areafk = models.ForeignKey(Area, on_delete=models.CASCADE, null=True, blank=True)
    name = models.TextField()
    shortname = models.TextField(blank=True)

    class Meta:
        verbose_name = "HQIP SECTION"
        verbose_name_plural = "HQIP SECTION"

    def __str__(self):
        return self.name

class Standards(models.Model):
    sectionfk = models.ForeignKey(Section, on_delete=models.CASCADE, null=True, blank=True)
    name = models.TextField()
    shortname = models.TextField(blank=True)

    class Meta:
        verbose_name = "HQIP STANDARD"
        verbose_name_plural = "HQIP STANDARD"

    def __str__(self):
        return self.name
    
class Score(models.Model):
    name = models.TextField()
    shorname = models.TextField(blank=True)

    class Meta:
        verbose_name = "HQIP SCORE"
        verbose_name_plural = "HQIP SCORE"

    def __str__(self):
        return self.name
     
class Criteria(models.Model):
    standardfk = models.ForeignKey(Standards, on_delete=models.CASCADE, null=True, blank=True)
    scorefk = models.ForeignKey(Score, on_delete=models.CASCADE)
    name = models.TextField()
    shortname = models.TextField(blank=True)
    namedari = models.TextField(blank=True)
    createdby = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "HQIP CRITERIA"
        verbose_name_plural = "HQIP CRITERIA"

    def __str__(self):
        return self.name
    
class ThematicMentorship(models.Model):
    name = models.CharField()
    shortname = models.CharField

    class Meta:
        verbose_name = "MENTORSHIP THEMATIC AREA"
        verbose_name_plural = "MENTORSHIP THEMATIC AREA"

    def __str__(self):
        return self.name
    
class MentorshipTopics(models.Model):
    thematicfk = models.ForeignKey(ThematicMentorship, on_delete=models.CASCADE, null=True, blank=True)
    shortname = models.CharField(null=True, blank=True)
    name = models.TextField()
    namedari = models.TextField(null=True, blank=True)
    namepashto = models.TextField(null=True, blank=True)
    nameeng= models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "MENTORSHIP TOPIC"
        verbose_name_plural = "MENTORSHIP TOPIC"

    def __str__(self):
        return self.name

class Mentorshipvisit(models.Model):
    facilityfk = models.ForeignKey(Facility, on_delete=models.CASCADE)
    visitdate = models.DateField()
    visitround = models.IntegerField(null=True, blank=True)
    mentorshipstarttime = models.TimeField()
    mentorshipendtime = models.TimeField()

    class Meta:
        verbose_name = "MENTORSHIP VISIT"
        verbose_name_plural = "MENTORSHIP VISIT"

    def __str__(self):
        return f"Mentorship Visit Date {self.visitdate}"
    
class Position(models.Model):
    name = models.CharField()

    class Meta:
        verbose_name = "STAFF PROFESSION"
        verbose_name_plural = "STAFF PROFESSION"

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

    class Meta:
        verbose_name = "STAFF JOB TITLE"
        verbose_name_plural = "STAFF JOB TITLE"

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

    class Meta:
        verbose_name = "MENTORSHIP DETAIL"
        verbose_name_plural = "MENTORSHIP DETAIL"

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

    class Meta:
        verbose_name = "HQIP ASSESSMENT"
        verbose_name_plural = "HQIP ASSESSMENT"

    def __str__(self):
        return self.remarks
    
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

    class Meta:
        verbose_name = "MPDSR"
        verbose_name_plural = "MPDSR"

    def __str__(self):
        return f"{self.facilityname} {self.monthmpdsr}" 
    
# class Gancohort(models.Model):
#     facilityname = models.ForeignKey(Facility, on_delete=models.CASCADE, verbose_name="Health Facility Name")
#     cohortname = models.TextField()
#     cohortnumber = models.IntegerField()
#     cohortstatus = models.TextField()
#     cohortchecklist = models.TextField()
#     cohortcreatedby = models.TextField()
#     remarks = models.TextField(blank=True, null=True)

#     def __str__(self):
#         return self.cohortname
    
# class Gancenrollment(models.Model):
#     cohortname = models.ForeignKey(Gancohort, on_delete=models.CASCADE, verbose_name="Cohort Name")
#     enrollmentid= models.IntegerField(blank=True, null=True)
#     name = models.TextField()
#     fathername = models.TextField()
#     contactnumber = models.TextField()
#     address = models.TextField()
#     gafirstanc = models.IntegerField()
#     edd = models.DateField()
#     remarks = models.TextField(blank=True, null=True)

#     def __str__(self):
#         return self.name
    
# class Gancfirstsession(models.Model):
#     registerid = models.ForeignKey(Gancenrollment, on_delete=models.CASCADE, verbose_name="Register Name")
#     sessiontype = models.TextField()
#     sessionround = models.IntegerField()
#     sessiondate = models.DateField()
#     attendance = models.TextField(verbose_name="Attendance (Group/Individual/No)")
#     presentga = models.IntegerField(verbose_name="Present_GA")
#     bp = models.TextField()
#     dhypertension = models.TextField(verbose_name="Diagnosed with hypertension (Y/N)")
#     rhypertensiontoMD = models.TextField(verbose_name="Referred  hypertension to MD (Y/N)")
#     weight = models.IntegerField(verbose_name="Weight")
#     anemia = models.TextField(verbose_name="Anemia (Y/N)")
#     ironfolate = models.TextField(verbose_name="Iron Folate/routine Dose(Y/N)")
#     ironfolatepluswomen = models.TextField(verbose_name="Iron folate (30+) for anemic woman(Y/N)")
#     pcalcium = models.TextField(verbose_name="Prescribe-Calcium(Y/N)")
#     acalcium = models.TextField(verbose_name="absorbed calcium in the last month(Y/N)")
#     muac = models.TextField(verbose_name="MUAC")
#     dmam = models.TextField(verbose_name="Diagnosed with MAM (Y/N)")
#     rmam = models.TextField(verbose_name="Refer MAM to Nutrition Counsellor (Y/N))")
#     dsam = models.TextField(verbose_name="Diagnosed with SAM (Y/N)")
#     rsam = models.TextField(verbose_name="Refer SAM to higher level (Y/N)")
#     clabexm = models.TextField(verbose_name="Completing Laboratory Exam (Y/N)")
#     hemoglobin = models.TextField(verbose_name="Hemoglobin")
#     urinexam = models.TextField(verbose_name="Urine exam/Protein Uria (NO/+,++,+++)")
#     rpositivepuriatomd = models.TextField(verbose_name="Referred  Positive Protin Uria to MD (Y/N)")
#     coughmorethantwoweeks= models.TextField(verbose_name="cough for more than two weeks(Y/N)")
#     rcough = models.TextField(verbose_name="Referred cough for more than two week to DOTS Room")
#     ttvaccine = models.TextField(verbose_name="TT vaccine (Y/N)")
#     dangersign = models.TextField(verbose_name="Danger signs during pregnancy (Y/N) ")
#     typeofdangersign = models.TextField(verbose_name="Type of Danger sign")
#     remarks = models.TextField(blank=True, null=True)

#     def __str__(self):
#         return self.sessiontype
    
# class Gancsecondsession(models.Model):
#     registerid = models.ForeignKey(Gancenrollment, on_delete=models.CASCADE, verbose_name="Register Name")
#     sessiontype = models.TextField()
#     sessionround = models.IntegerField()
#     sessiondate = models.DateField()
#     attendance = models.TextField(verbose_name="Attendance (Group/Individual/No)")
#     presentga = models.IntegerField(verbose_name="Present_GA")
#     bp = models.TextField()
#     dhypertension = models.TextField(verbose_name="Diagnosed with hypertension (Y/N)")
#     rhypertensiontoMD = models.TextField(verbose_name="Referred  hypertension to MD (Y/N)")
#     weight = models.IntegerField(verbose_name="Weight")
#     anemia = models.TextField(verbose_name="Anemia (Y/N)")
#     ironfolate = models.TextField(verbose_name="Iron Folate/routine Dose(Y/N)")
#     ironfolatepluswomen = models.TextField(verbose_name="Iron folate (30+) for anemic woman(Y/N)")
#     pcalcium = models.TextField(verbose_name="Prescribe-Calcium(Y/N)")
#     acalcium = models.TextField(verbose_name="absorbed calcium in the last month(Y/N)")
#     mebendazole = models.TextField(verbose_name="Mebendazole (Y/N)") 
#     muac = models.TextField(verbose_name="MUAC")
#     dmam = models.TextField(verbose_name="Diagnosed with MAM (Y/N)")
#     rmam = models.TextField(verbose_name="Refer MAM to Nutrition Counsellor (Y/N))")
#     dsam = models.TextField(verbose_name="Diagnosed with SAM (Y/N)")
#     rsam = models.TextField(verbose_name="Refer SAM to higher level (Y/N)")
#     urinexam = models.TextField(verbose_name="Urine exam/Protein Uria (NO/+,++,+++)")
#     rpositivepuriatomd = models.TextField(verbose_name="Referred  Positive Protin Uria to MD (Y/N)")
#     coughmorethantwoweeks= models.TextField(verbose_name="cough for more than two weeks(Y/N)")
#     rcough = models.TextField(verbose_name="Referred cough for more than two week to DOTS Room")
#     ttvaccine = models.TextField(verbose_name="TT vaccine (Y/N)")
#     dangersign = models.TextField(verbose_name="Danger signs during pregnancy (Y/N) ")
#     typeofdangersign = models.TextField(verbose_name="Type of Danger sign")   
#     remarks = models.TextField(blank=True, null=True)

#     def __str__(self):
#         return self.sessiontype
    
# class Gancthirdsession(models.Model):
#     registerid = models.ForeignKey(Gancenrollment, on_delete=models.CASCADE, verbose_name="Register Name")
#     sessiontype = models.TextField()
#     sessionround = models.IntegerField()
#     sessiondate = models.DateField()
#     attendance = models.TextField(verbose_name="Attendance (Group/Individual/No)")
#     presentga = models.IntegerField(verbose_name="Present_GA")
#     bp = models.TextField()
#     dhypertension = models.TextField(verbose_name="Diagnosed with hypertension (Y/N)")
#     rhypertensiontoMD = models.TextField(verbose_name="Referred  hypertension to MD (Y/N)")
#     weight = models.IntegerField(verbose_name="Weight")
#     anemia = models.TextField(verbose_name="Anemia (Y/N)")
#     ironfolate = models.TextField(verbose_name="Iron Folate/routine Dose(Y/N)")
#     ironfolatepluswomen = models.TextField(verbose_name="Iron folate (30+) for anemic woman(Y/N)")
#     pcalcium = models.TextField(verbose_name="Prescribe-Calcium(Y/N)")
#     acalcium = models.TextField(verbose_name="absorbed calcium in the last month(Y/N)")
#     muac = models.TextField(verbose_name="MUAC")
#     dmam = models.TextField(verbose_name="Diagnosed with MAM (Y/N)")
#     rmam = models.TextField(verbose_name="Refer MAM to Nutrition Counsellor (Y/N))")
#     dsam = models.TextField(verbose_name="Diagnosed with SAM (Y/N)")
#     rsam = models.TextField(verbose_name="Refer SAM to higher level (Y/N)")
#     antedepressionscreening = models.TextField( verbose_name="Antenatal Depression Screening (Y/N)")
#     antedepressiondiagnosed = models.TextField( verbose_name="Antenatal Depression Diagnosed (Y/N)")
#     rpsychosocialcounselor = models.TextField( verbose_name="Refer to the psychosocial counselor (Y/N)")
#     urinexam = models.TextField(verbose_name="Urine exam/Protein Uria (NO/+,++,+++)")
#     rpositivepuriatomd = models.TextField(verbose_name="Referred  Positive Protin Uria to MD (Y/N)")
#     coughmorethantwoweeks= models.TextField(verbose_name="cough for more than two weeks(Y/N)")
#     rcough = models.TextField(verbose_name="Referred cough for more than two week to DOTS Room")
#     ttvaccine = models.TextField(verbose_name="TT vaccine (Y/N)")
#     dangersign = models.TextField(verbose_name="Danger signs during pregnancy (Y/N) ")
#     typeofdangersign = models.TextField(verbose_name="Type of Danger sign") 
#     birthplanningcounseling = models.TextField(verbose_name="Birth Planning Counseling (Y/N) ") 
#     remarks = models.TextField(blank=True, null=True)

#     def __str__(self):
#         return self.sessiontype
    
class aimpee(models.Model):
    shamsimonth = models.CharField()
    shamsiyear = models.CharField()
    period = models.CharField()
    bl_progress = models.CharField()
    aimfacilityname = models.ForeignKey(Facility, on_delete=models.CASCADE, verbose_name="Health Facility Name")
    gre_month =models.CharField()
    gre_year= models.CharField()
    afiat_flag = models.BooleanField()

      # ANC / Pre-E core indicators
    num_anc_preg_seen = models.BigIntegerField(default=0, verbose_name="Number of pregnant women seen in ANC")
    num_anc_bp_taken = models.BigIntegerField(default=0, verbose_name="Number of ANC women who had their blood pressure taken")
    num_anc_pree_dx = models.BigIntegerField(default=0, verbose_name="Number of ANC women with Pre-E diagnosed (BP>140/90, 2+ proteinuria)")
    num_severe_pe_e_bp160 = models.BigIntegerField(default=0, verbose_name="Number of patients with Severe Pre-Eclampsia or Eclampsia WITH BP > 160 systolic OR 110 diastolic")
    num_severe_pe_e_bp160_tx1h = models.BigIntegerField(default=0, verbose_name="Number of Severe Pre-E/E patients (BP >160/110) who received antihypertensive medication within one hour of diagnosis")
    num_anc_pree_admit = models.BigIntegerField(default=0, verbose_name="Number of patients with Pre-E diagnosed in ANC clinic who required admission")
    num_spe_admit_before_delivery = models.BigIntegerField(default=0, verbose_name="Number of patients admitted to HFs with Severe Pre-Eclampsia (SPE) before delivery")
    num_eclampsia_admit_before_delivery = models.BigIntegerField(default=0, verbose_name="Number of patients admitted to HFs with Eclampsia before delivery")
    num_spe_e_mgso4_1h = models.BigIntegerField(default=0, verbose_name="Number of patients with Severe Pre-E or Eclampsia who received Magnesium Sulfate within one hour of diagnosis")
    num_spe_at_birth = models.BigIntegerField(default=0, verbose_name="Number of patients with Severe Pre-E at birth (including referrals in)")
    num_eclampsia_at_birth = models.BigIntegerField(default=0, verbose_name="Number of patients with Eclampsia from ANC, Labor, PNC or referred in")
    num_chronic_htn_superimposed_pe = models.BigIntegerField(default=0, verbose_name="Number of patients with chronic hypertension with superimposed pre-eclampsia")
    num_gest_htn = models.BigIntegerField(default=0, verbose_name="Gestational hypertension")
    num_spe_deliv_24h = models.BigIntegerField(default=0, verbose_name="Number of Severe Pre-E patients who delivered within 24 hours of admission")
    num_eclampsia_deliv_12h = models.BigIntegerField(default=0, verbose_name="Number of Eclampsia patients who delivered within 12 hours of admission")
    num_spe_e_fu_3d = models.BigIntegerField(default=0, verbose_name="Number of patients with SPE or Eclampsia who had a follow-up visit within 3 days after delivery discharge")
    num_spe_e_pp_dx = models.BigIntegerField(default=0, verbose_name="Number of patients with SPE or Eclampsia diagnosed during the postpartum period")

    # Complications
    comp_renal_failure = models.BigIntegerField(default=0, verbose_name="Renal Failure (less than 30 ml/hr for 4 hours despite fluid challenge)")
    comp_pulmonary_edema = models.BigIntegerField(default=0, verbose_name="Pulmonary edema")
    comp_eclamptic_seizure = models.BigIntegerField(default=0, verbose_name="Eclamptic seizure")
    comp_stroke = models.BigIntegerField(default=0, verbose_name="Stroke (Cerebral hemorrhage or blood clot in brain)")
    comp_thrombocytopenia = models.BigIntegerField(default=0, verbose_name="Thrombocytopenia (not HELLP)")
    comp_hellp = models.BigIntegerField(default=0, verbose_name="HELLP syndrome")
    comp_pres = models.BigIntegerField(default=0, verbose_name="PRES (Posterior Reversible Encephalopathy Syndrome)")
    comp_iufd = models.BigIntegerField(default=0, verbose_name="Intrauterine Fetal Death")
    comp_placental_abruption = models.BigIntegerField(default=0, verbose_name="Placental abruption")
    comp_eclamptic_coma = models.BigIntegerField(default=0, verbose_name="Eclamptic coma")
    comp_total = models.BigIntegerField(default=0, verbose_name="Total complications due to SPE and Eclampsia")
    maternal_death_spe_e = models.BigIntegerField(default=0, verbose_name="Maternal death due to SPE or Eclampsia")

    # Outpatient / OPD management
    num_opd_pree_dx_md = models.BigIntegerField(default=0, verbose_name="Number of outpatients diagnosed in OPD with Pre-Eclampsia by MD")
    num_opd_pree_twice_week = models.BigIntegerField(default=0, verbose_name="Number of outpatients with Pre-Eclampsia who returned to ANC/OPD twice a week")
    num_opd_pree_weekly_labs = models.BigIntegerField(default=0, verbose_name="Number of outpatients with Pre-Eclampsia who received weekly laboratory testing")
    pct_opd_pree_weekly_labs = models.BigIntegerField(default=0, verbose_name="Percentage of outpatients with Pre-Eclampsia who received weekly laboratory testing")

    # Advanced interventions
    ai_aortic_compression = models.BigIntegerField(default=0, verbose_name="Aortic compression")
    ai_ubt = models.BigIntegerField(default=0, verbose_name="UBT (condom catheter)")
    ai_lac_repair = models.BigIntegerField(default=0, verbose_name="Repair of severe vaginal or cervical lacerations causing a PPH")
    ai_blynch_ual = models.BigIntegerField(default=0, verbose_name="B-Lynch suture or uterine artery ligation")
    ai_nasg = models.BigIntegerField(default=0, verbose_name="Anti-shock garment (NASG)")
    ai_ruptured_uterus_repair = models.BigIntegerField(default=0, verbose_name="Repair ruptured uterus")
    ai_pph_hysterectomy = models.BigIntegerField(default=0, verbose_name="Postpartum hysterectomy for hemorrhage")
    ai_hysterectomy_other = models.BigIntegerField(default=0, verbose_name="Postpartum hysterectomy (other causes)")
    ai_total = models.BigIntegerField(default=0, verbose_name="Total number of advanced interventions conducted")
        
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
        verbose_name="Number of ALL births (log book)"
    )
    births_vaginal = models.BigIntegerField(
        default=0,
        verbose_name="Number of births - by vaginal delivery"
    )
    births_csection = models.BigIntegerField(
        default=0,
        verbose_name="Number of births - by C-sections"
    )
    oxytocin_immediate = models.BigIntegerField(
        default=0,
        verbose_name="Number of patients receiving oxytocin immediately after birth"
    )
    antepartum_hemorrhage = models.BigIntegerField(
        default=0,
        verbose_name="Number of Antepartum Hemorrhage (Abruption, Placenta Previa)"
    )

    # PPH by mode of delivery / referrals
    pph_vaginal_501_999 = models.BigIntegerField(
        default=0,
        verbose_name="Number of Postpartum Hemorrhage (PPH) - after vaginal delivery (501–999 cc)"
    )
    pph_cs_1000_plus = models.BigIntegerField(
        default=0,
        verbose_name="Number of Postpartum Hemorrhage (PPH) - after Cesarean delivery (≥1000 cc)"
    )
    pph_referral_in_outside_aim = models.BigIntegerField(
        default=0,
        verbose_name="Number of Postpartum Hemorrhage (PPH) referrals in from outside of AIM facilities"
    )
    pph_referral_in_aim = models.BigIntegerField(
        default=0,
        verbose_name="Number of Postpartum Hemorrhage (PPH) referrals in from AIM facilities"
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

    class Meta:
        verbose_name = "AIM-PPH"
        verbose_name_plural = "AIM-PPH"

    def __str__(self):
        return f"AIM-PPH #{self.id}"

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

    class Meta:
        verbose_name = "SAFE SURGERY"
        verbose_name_plural = "SAFE SURGERY"

    def __str__(self):
        return f"SAFE SURGERY #{self.pk or ''}"

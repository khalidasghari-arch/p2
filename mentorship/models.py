from django.db import models

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
    facilityfk = models.ForeignKey("hiva.Facility", on_delete=models.CASCADE)
    visitdate = models.DateField()
    visitround = models.IntegerField(null=True, blank=True)
    mentorshipstarttime = models.TimeField()
    mentorshipendtime = models.TimeField()

    class Meta:
        verbose_name = "MENTORSHIP VISIT"
        verbose_name_plural = "MENTORSHIP VISIT"

    def __str__(self):
        return f"Mentorship Visit Date {self.visitdate}"

class Staff(models.Model):
    hfname = models.ForeignKey("hiva.Facility", on_delete=models.CASCADE)
    firstname = models.CharField()
    lastname = models.CharField(blank=True, null=True)
    position = models.ForeignKey('hiva.Position', on_delete=models.CASCADE)
    tazkiranumber = models.CharField(blank=True, null=True)
    gender = models.BooleanField(
        choices=[
            (True, "Female"),
            (False, "Male"),
        ],
        default=True,
        verbose_name="Gender", 
        blank=True, null=True)
    status = models.BooleanField(
          choices=[
            (True, "Active"),
            (False, "Inactive"),
        ],
        default=True,
        verbose_name="Status", 
        blank=True, null=True)

    class Meta:
        verbose_name = "MENTEE"
        verbose_name_plural = "MENTEE"

    def __str__(self):
        return self.firstname

class Mentorshipdetails(models.Model):
    mentorshipvistfk = models.ForeignKey(Mentorshipvisit, on_delete=models.CASCADE, related_name="items", null=True, blank=True)
    menteename = models.ForeignKey(Staff, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Mentee")
    thematicname = models.ForeignKey(ThematicMentorship, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Mentorship Thematic Area") 
    topicname = models.ForeignKey(MentorshipTopics, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Topic") 
    mentor = models.ForeignKey("hiva.Assessor", on_delete=models.CASCADE, null=True, blank=True, verbose_name="Mentor")
    ls = models.BooleanField(verbose_name="Learning Session")
    pc = models.BooleanField(verbose_name="Patient Competent")
    mc = models.BooleanField(verbose_name="Model Compotent")

    class Meta:
        verbose_name = "MENTORSHIP DETAIL"
        verbose_name_plural = "MENTORSHIP DETAIL"

    def __int__(self):
        return self.id

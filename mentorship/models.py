from django.db import models
from django.core.exceptions import ValidationError

class ThematicMentorship(models.Model):
    name = models.CharField(max_length=255, verbose_name="Mentorship Thematic Area")
    shortname = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = "MENTORSHIP THEMATIC AREA"
        verbose_name_plural = "MENTORSHIP THEMATIC AREA"

    def __str__(self):
        return self.name

class MentorshipTopics(models.Model):
    thematicfk = models.ForeignKey(ThematicMentorship, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Mentorship Thematic Area")
    shortname = models.CharField(max_length=50, null=True, blank=True)
    name = models.CharField(max_length=50, verbose_name="Topic code")
    namedari = models.TextField(null=True, blank=True)
    namepashto = models.TextField(null=True, blank=True)
    nameeng = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "MENTORSHIP TOPIC"
        verbose_name_plural = "MENTORSHIP TOPIC"

    def __str__(self):
        return self.name

class Mentorshipvisit(models.Model):
    facilityfk = models.ForeignKey("hiva.Facility", on_delete=models.CASCADE, verbose_name="Health Facility")
    visitdate = models.DateField(verbose_name="Visit Date")
    visitround = models.IntegerField(null=True, blank=True, verbose_name="Visit Round")
    mentorshipstarttime = models.TimeField(verbose_name="Mentorship Start Time")
    mentorshipendtime = models.TimeField(verbose_name="Mentorship End Time")

    class Meta:
        verbose_name = "MENTORSHIP VISIT"
        verbose_name_plural = "MENTORSHIP VISIT"

    def __str__(self):
        return f"{self.facilityfk} - {self.visitdate}"

class Staff(models.Model):
    hfname = models.ForeignKey("hiva.Facility", on_delete=models.CASCADE, verbose_name="Health Facility")
    firstname = models.CharField(max_length=100, verbose_name="First Name")
    lastname = models.CharField(max_length=100, blank=True, null=True, verbose_name="Last Name")
    position = models.ForeignKey('hiva.Position', on_delete=models.CASCADE, verbose_name="Position")
    tazkiranumber = models.CharField(max_length=100, blank=True, null=True, verbose_name="Tazkira Number", unique=True)

    gender = models.BooleanField(
        choices=[(True, "Female"), (False, "Male")],
        default=True,
        verbose_name="Gender",
        blank=True, null=True
    )
    status = models.BooleanField(
        choices=[(True, "Active"), (False, "Inactive")],
        default=True,
        verbose_name="Status",
        blank=True, null=True
    )

    class Meta:
        verbose_name = "MENTEE"
        verbose_name_plural = "MENTEE"

    def __str__(self):
        full = f"{self.firstname} {self.lastname or ''}".strip()
        return full


class Mentorshipdetails(models.Model):
    mentorshipvistfk = models.ForeignKey(
    Mentorshipvisit, on_delete=models.CASCADE, related_name="items", null=True, blank=True)
    menteename = models.ForeignKey(Staff, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Mentee")
    thematicname = models.ForeignKey(ThematicMentorship, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Mentorship Thematic Area")
    topicname = models.ForeignKey(MentorshipTopics, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Topic code")
    mentor = models.ForeignKey("hiva.Assessor", on_delete=models.CASCADE, null=True, blank=True, verbose_name="Mentor")

    ls = models.BooleanField(default=False, verbose_name="Learning Session")
    pc = models.BooleanField(default=False, verbose_name="Patient Competent")
    mc = models.BooleanField(default=False, verbose_name="Model Competent")

    class Meta:
        verbose_name = "MENTORSHIP DETAIL"
        verbose_name_plural = "MENTORSHIP DETAIL"

    def clean(self):
        selected = sum([bool(self.ls), bool(self.pc), bool(self.mc)])
        if selected > 1:
            raise ValidationError("Only ONE of (LS, PC, MC) can be selected for each mentorship detail.")

    def __str__(self):
        return f"Detail #{self.pk}"

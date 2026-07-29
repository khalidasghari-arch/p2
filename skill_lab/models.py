from datetime import datetime, timedelta
from django.core.exceptions import ValidationError
from django.db import models

class ThematicArea(models.Model):
    name = models.CharField(max_length=255, verbose_name="Mentorship Thematic Area")
    shortname = models.CharField(max_length=50, blank=True, null=True)
    hqip_area = models.ForeignKey(
        "hiva.Area",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="skill_lab_thematics",
        verbose_name="Mapped HQIP Thematic Area",
    )

    class Meta:
        verbose_name = "MENTORSHIP THEMATIC AREA"
        verbose_name_plural = "MENTORSHIP THEMATIC AREA"
        ordering = ["name"]

    def __str__(self):
        return self.name

class SkillLabTopic(models.Model):
    thematicfk = models.ForeignKey(
        ThematicArea,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Mentorship Thematic Area",
        related_name="topics",
    )
    shortname = models.CharField(max_length=50, null=True, blank=True)
    name = models.CharField(max_length=50, verbose_name="Topic code")
    namedari = models.TextField(null=True, blank=True)
    namepashto = models.TextField(null=True, blank=True)
    nameeng = models.TextField(null=True, blank=True)
    track = models.CharField(max_length=20, blank=True, default="")
    seq_no = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "MENTORSHIP TOPIC"
        verbose_name_plural = "MENTORSHIP TOPIC"
        ordering = ["track", "seq_no", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["thematicfk", "name"],
                name="unique_skilllabtopic_thematic_name",
            )
        ]

    def __str__(self):
        return self.name

class SkillLab(models.Model):
    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("INACTIVE", "Inactive"),
        ("PLANNED", "Planned"),
        ("CLOSED", "Closed"),
    ]

    name = models.CharField(max_length=255, verbose_name="Skill Lab Name", unique=True)
    facility = models.ForeignKey(
        "hiva.Facility",
        on_delete=models.PROTECT,
        related_name="skill_labs",
        verbose_name="Facility",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="ACTIVE",
        verbose_name="Skill Lab Status",
    )
    implementing_partner = models.ForeignKey(
        "hiva.Implementor",
        on_delete=models.PROTECT,
        related_name="skilllabs",
        blank=True,
        null=True,
        verbose_name="Mentor Organization",
    )
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["facility__name", "name"]
        #nique_together = ("facility", "name")
        verbose_name = "MNH SKILL LAB"
        verbose_name_plural = "MNH SKILL LAB"

    def __str__(self):
        return f"{self.name} - {self.facility.name}"

    @property
    def province(self):
        if self.facility and getattr(self.facility, "districtfk", None) and getattr(self.facility.districtfk, "provincefk", None):
            return self.facility.districtfk.provincefk
        return None

    @property
    def district(self):
        if self.facility and getattr(self.facility, "districtfk", None):
            return self.facility.districtfk
        return None

class Skill_Lab_Mentee(models.Model):
    hfname = models.ForeignKey("hiva.Facility", on_delete=models.CASCADE, verbose_name="Health Facility")
    firstname = models.CharField(max_length=100, verbose_name="First Name")
    lastname = models.CharField(max_length=100, blank=True, null=True, verbose_name="Last Name")
    fathername = models.CharField(max_length=200, blank=True, null=True, verbose_name="Father Name")
    position = models.ForeignKey("hiva.Position", on_delete=models.CASCADE, verbose_name="Position")
    tazkiranumber = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Tazkira Number",
        unique=True,
    )
    gender = models.BooleanField(
        choices=[(True, "Female"), (False, "Male")],
        default=True,
        verbose_name="Gender",
        blank=True,
        null=True,
    )
    status = models.BooleanField(
        choices=[(True, "Active"), (False, "Inactive")],
        default=True,
        verbose_name="Status",
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = "MENTEE"
        verbose_name_plural = "MENTEE"
        ordering = ["firstname", "lastname"]

    def __str__(self):
        return f"{self.firstname} {self.lastname or ''}".strip()

class SkillLabSession(models.Model):
    SESSION_TYPE_CHOICES = [
        ("Group", "Group"),
        ("Individual", "Individual"),
    ]

    skill_lab = models.ForeignKey(
        SkillLab,
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    session_date = models.DateField(verbose_name="Date")
    lab_round = models.PositiveIntegerField(verbose_name="Lab Round")

    check_in = models.TimeField(blank=True, null=True, verbose_name="Check In")
    check_out = models.TimeField(blank=True, null=True, verbose_name="Check Out")

    session_type = models.CharField(
        max_length=20,
        choices=SESSION_TYPE_CHOICES,
        verbose_name="Session Type",
    )
    
    mentor_name = models.ForeignKey(
    "hiva.Assessor",
    on_delete=models.PROTECT,
    related_name="skilllab_sessions",
    blank=True,
    null=True,
    verbose_name="Clinical Mentor",
    )

    mentor_org = models.ForeignKey(
        "hiva.Implementor",
        on_delete=models.PROTECT,
        related_name="skilllab_sessions",
        blank=True,
        null=True,
        verbose_name="Mentor Organization",
    )

    ce_checklist_applied = models.BooleanField(default=False, verbose_name="CE Checklist Applied")
    planned_session = models.BooleanField(default=False)
    completed_session = models.BooleanField(default=True)
    total_participants = models.PositiveIntegerField(default=0)
    objectives = models.TextField(blank=True, null=True)
    session_notes = models.TextField(blank=True, null=True)
    challenges = models.TextField(blank=True, null=True)
    action_points = models.TextField(blank=True, null=True)
    followup_needed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-session_date", "skill_lab__name"]
        verbose_name = "MNH SKILL LAB SESSION"
        verbose_name_plural = "MNH SKILL LAB SESSION"
        indexes = [
            models.Index(fields=["session_date"]),
            models.Index(fields=["lab_round"]),
        ]

    def __str__(self):
        return f"{self.skill_lab.name} - Round {self.lab_round} - {self.session_date}"

    @property
    def facility(self):
        return self.skill_lab.facility if self.skill_lab_id else None

    @property
    def province(self):
        return self.skill_lab.province if self.skill_lab_id else None

    @property
    def district(self):
        return self.skill_lab.district if self.skill_lab_id else None

    @property
    def duration_hours(self):
        if self.check_in and self.check_out:
            start = datetime.combine(self.session_date, self.check_in)
            end = datetime.combine(self.session_date, self.check_out)
            delta = end - start
            return round(delta.total_seconds() / 3600, 2)
        return None

    def clean(self):
        if self.check_in and self.check_out:
            start = datetime.combine(self.session_date or datetime.today().date(), self.check_in)
            end = datetime.combine(self.session_date or datetime.today().date(), self.check_out)

            if end < start:
                raise ValidationError({"check_out": "Check-out cannot be earlier than check-in."})

            if end - start > timedelta(hours=12):
                raise ValidationError("Session duration looks too long (>12 hours). Please verify check-in/check-out.")

class SkillLabDashboard(SkillLabSession):
    class Meta:
        proxy = True
        verbose_name = "Skill Lab Dashboard"
        verbose_name_plural = "Skill Lab Dashboard"

class SkillLabParticipantRecord(models.Model):
    GENDER_CHOICES = [
        ("FEMALE", "Female"),
        ("MALE", "Male"),
    ]

    COMPETENCY_STATUS_CHOICES = [
        ("NOT_STARTED", "Not Started"),
        ("IN_PROGRESS", "In Progress"),
        ("COMPETENT", "Competent"),
        ("NEEDS_REPEAT", "Needs Repeat"),
    ]

    session = models.ForeignKey(
        SkillLabSession,
        on_delete=models.CASCADE,
        related_name="participant_records",
    )

    mentee_name = models.ForeignKey(
        Skill_Lab_Mentee,
        on_delete=models.PROTECT,
        related_name="skill_lab_records",
        verbose_name="Mentee Name",
    )

    thematic_area = models.ForeignKey(
        ThematicArea,
        on_delete=models.PROTECT,
        related_name="participant_records",
    )
    topic = models.ForeignKey(
        SkillLabTopic,
        on_delete=models.PROTECT,
        related_name="participant_records",
    )

    ls = models.BooleanField(default=False, verbose_name="LS")
    mc = models.BooleanField(default=False, verbose_name="MC")

    competency_status = models.CharField(
        max_length=30,
        choices=COMPETENCY_STATUS_CHOICES,
        default="IN_PROGRESS",
    )
    pre_test_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    post_test_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    demonstration_done = models.BooleanField(default=False)
    return_demonstration_done = models.BooleanField(default=False)
    checklist_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    feedback_given = models.BooleanField(default=False)
    next_followup_date = models.DateField(blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["session__session_date", "mentee_name"]
        verbose_name = "MNH SKILL LAB RECORD"
        verbose_name_plural = "MNH SKILL LAB RECORD"
        constraints = [
            models.UniqueConstraint(
                fields=["session", "mentee_name", "topic"],
                name="unique_skilllab_session_mentee_topic",
            )
        ]

    def __str__(self):
        return f"{self.mentee_name} - {self.topic.name} - {self.session.session_date}"

    @property
    def facility(self):
        return self.session.facility if self.session_id else None

    def clean(self):
        methods_selected = sum([bool(self.ls), bool(self.mc)])

        if methods_selected == 0:
            raise ValidationError("At least one of LS or MC must be selected.")

        if methods_selected > 1:
            raise ValidationError("Only one of LS or MC should be selected for each record.")

        if self.topic and self.thematic_area and self.topic.thematicfk_id != self.thematic_area_id:
            raise ValidationError({
                "topic": "Selected topic does not belong to the selected thematic area."
            })
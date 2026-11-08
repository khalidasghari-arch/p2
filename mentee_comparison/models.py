from django.conf import settings
from django.db import models

class MenteeMatch(models.Model):
    staff = models.OneToOneField('mentorship.Staff', on_delete=models.CASCADE)
    skill_mentee = models.OneToOneField(
        getattr(settings, 'MENTEE_COMPARISON_SKILL_MODEL', 'skill_lab.Skill_Lab_Mentee'),
        on_delete=models.CASCADE,
    )
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True,
                                     on_delete=models.SET_NULL)
    confirmed_at = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=500, blank=True)

    class Meta:
        verbose_name = 'MENTEE COMPARISON DASHBOARD'
        verbose_name_plural = 'MENTEE COMPARISON DASHBOARD'
        permissions = [('confirm_matches', 'Can confirm and remove mentee comparison links')]

    def __str__(self):
        return f'{self.staff} / {self.skill_mentee}'

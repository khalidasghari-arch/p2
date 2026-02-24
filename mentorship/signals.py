from django.db.models.signals import post_save
from django.dispatch import receiver
from mentorship.models import Mentorshipdetails, MenteeTopicStatus

@receiver(post_save, sender=Mentorshipdetails)
def update_status_on_save(sender, instance, created, **kwargs):

    if not instance.menteename or not instance.topicname:
        return

    status, _ = MenteeTopicStatus.objects.get_or_create(
        mentee=instance.menteename,
        topic=instance.topicname,
        defaults={
            "status": "NOT_STARTED",
            "consecutive_ls": 0,
        }
    )
    # LS
    if instance.ls:
        status.consecutive_ls += 1
        status.status = "IN_PROGRESS"

    # PC / MC
    if instance.pc or instance.mc:
        status.status = "COMPETENT"
        status.consecutive_ls = 0

    status.save()
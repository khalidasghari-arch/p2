from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Mentorshipdetails, MenteeTopicStatus

@receiver(post_save, sender=Mentorshipdetails)
def update_mentee_topic_status(sender, instance: Mentorshipdetails, created, **kwargs):
    mentee = instance.menteename
    topic = instance.topicname
    if not mentee or not topic:
        return

    if instance.ls:
        stype = "LS"
    elif instance.pc:
        stype = "PC"
    elif instance.mc:
        stype = "MC"
    else:
        return  # none selected

    obj, _ = MenteeTopicStatus.objects.get_or_create(mentee=mentee, topic=topic)

    obj.last_session_type = stype
    obj.last_date = timezone.localdate()

    if stype == "LS":
        if obj.status != "COMPETENT":
            obj.status = "IN_PROGRESS"
        obj.consecutive_ls = obj.consecutive_ls + 1
    else:
        obj.status = "COMPETENT"
        obj.competent_date = obj.competent_date or timezone.localdate()
        obj.consecutive_ls = 0

    obj.save()

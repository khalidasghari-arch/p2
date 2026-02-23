from django.core.management.base import BaseCommand
from django.db import transaction
from mentorship.models import (
    Mentorshipdetails,
    MenteeTopicStatus,
)

class Command(BaseCommand):
    help = "Rebuild MenteeTopicStatus from Mentorshipdetails (Production Safe)"

    @transaction.atomic
    def handle(self, *args, **kwargs):

        self.stdout.write(self.style.WARNING("Rebuilding MenteeTopicStatus..."))

        # Clear existing state safely
        MenteeTopicStatus.objects.all().delete()

        details = (
            Mentorshipdetails.objects
            .select_related("menteename", "topicname")
            .order_by("id")
        )

        for d in details:

            if not d.menteename or not d.topicname:
                continue

            status, created = MenteeTopicStatus.objects.get_or_create(
                mentee=d.menteename,
                topic=d.topicname,
                defaults={
                    "status": "IN_PROGRESS",
                    "consecutive_ls": 0,
                }
            )

            # ---- Learning Session ----
            if d.ls:
                status.consecutive_ls += 1

            # ---- Competency ----
            if d.pc or d.mc:
                status.status = "COMPETENT"
                status.consecutive_ls = 0

            status.save()

        self.stdout.write(self.style.SUCCESS("Rebuild complete."))
from django.core.management.base import BaseCommand
from django.db import transaction
from mentorship.models import Mentorshipdetails, MenteeTopicStatus

class Command(BaseCommand):
    help = "Rebuild MenteeTopicStatus from Mentorshipdetails (Chronological + Safe)"

    @transaction.atomic
    def handle(self, *args, **kwargs):

        self.stdout.write(self.style.WARNING("Rebuilding MenteeTopicStatus..."))

        # Clear safely
        MenteeTopicStatus.objects.all().delete()

        # Group details by (mentee, topic)
        details = (
            Mentorshipdetails.objects
            .select_related("menteename", "topicname", "mentorshipvistfk")
            .filter(menteename__isnull=False, topicname__isnull=False)
            .order_by(
                "menteename_id",
                "topicname_id",
                "mentorshipvistfk__visitdate",
                "id"
            )
        )

        current_key = None
        consecutive_ls = 0
        final_status = "NOT_STARTED"

        for d in details:

            key = (d.menteename_id, d.topicname_id)

            # When topic changes, save previous state
            if current_key and key != current_key:
                mentee_id, topic_id = current_key
                MenteeTopicStatus.objects.create(
                    mentee_id=mentee_id,
                    topic_id=topic_id,
                    status=final_status,
                    consecutive_ls=consecutive_ls if final_status != "COMPETENT" else 0,
                )
                consecutive_ls = 0
                final_status = "NOT_STARTED"

            current_key = key

            # ---- LS logic ----
            if d.ls:
                consecutive_ls += 1
                final_status = "IN_PROGRESS"

            # ---- Competency logic ----
            if d.pc or d.mc:
                final_status = "COMPETENT"
                consecutive_ls = 0

        # Save last group
        if current_key:
            mentee_id, topic_id = current_key
            MenteeTopicStatus.objects.create(
                mentee_id=mentee_id,
                topic_id=topic_id,
                status=final_status,
                consecutive_ls=consecutive_ls if final_status != "COMPETENT" else 0,
            )

        self.stdout.write(self.style.SUCCESS("Rebuild complete."))
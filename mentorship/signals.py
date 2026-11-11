import json
import logging
from urllib.request import Request, urlopen

from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse

from .models import (
    MenteeTopicStatus,
    Mentorshipdetails,
    MentorshipEmailRecipient,
    Staff,
)

logger = logging.getLogger(__name__)


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
        },
    )

    if instance.ls:
        status.consecutive_ls += 1
        status.status = "IN_PROGRESS"

    if instance.pc or instance.mc:
        status.status = "COMPETENT"
        status.consecutive_ls = 0

    status.save()


@receiver(post_save, sender=Staff, dispatch_uid="mentorship.staff_added_email")
def notify_mentee_added(sender, instance, created, raw, using, **kwargs):
    if not created or raw:
        return

    mentee_id = instance.pk

    def deliver():
        api_key = getattr(settings, "RESEND_API_KEY", "")
        from_address = getattr(settings, "MENTORSHIP_NOTIFICATION_FROM", "")
        base_url = getattr(settings, "MNHIMS_BASE_URL", "")

        if not all((api_key, from_address, base_url)):
            logger.warning("Mentorship email skipped: Render settings are incomplete.")
            return

        recipients = list(
            MentorshipEmailRecipient.objects.using(using)
            .filter(enabled=True)
            .values_list("email", flat=True)
        )
        if not recipients:
            return

        admin_path = reverse("admin:mentorship_staff_change", args=[mentee_id])
        record_url = f"{base_url.rstrip('/')}{admin_path}"

        for address in recipients:
            payload = {
                "from": from_address,
                "to": [address],
                "subject": "MNHIMS: New mentorship mentee registered",
                "text": (
                    "A new mentee has been registered in the MNHIMS "
                    "Mentorship module.\n\n"
                    "Sign in to MNHIMS to review the record:\n"
                    f"{record_url}\n"
                ),
            }
            request = Request(
                "https://api.resend.com/emails",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "MNHIMS/1.0",
                },
                method="POST",
            )

            try:
                with urlopen(request, timeout=5):
                    pass
            except OSError as exc:
                logger.warning(
                    "Mentorship email failed for Staff ID %s "
                    "(%s; HTTP status: %s).",
                    mentee_id,
                    type(exc).__name__,
                    getattr(exc, "code", None),
                )

    transaction.on_commit(deliver, using=using, robust=True)
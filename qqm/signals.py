from django.db.models.signals import post_save
from django.dispatch import receiver
from qqm.models import QQMUpload
from qqm.services.importer import process_qqm_upload


@receiver(post_save, sender=QQMUpload)
def auto_process_upload(sender, instance, created, **kwargs):
    if created and not instance.processed:
        try:
            process_qqm_upload(instance.id)
        except Exception as e:
            print(f"Processing failed: {e}")
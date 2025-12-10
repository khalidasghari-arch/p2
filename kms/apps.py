from django.apps import AppConfig

class KmsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "kms"

    def ready(self):
        from . import signals  # noqa

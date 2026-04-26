from django.apps import AppConfig

class QqmConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'qqm'

    def ready(self):
        import qqm.signals
import os

from django.core.wsgi import get_wsgi_application
from whitenoise import WhiteNoise
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tst.settings')

application = get_wsgi_application()

# Serve static files with WhiteNoise
BASE_DIR = Path(__file__).resolve().parent.parent
application = WhiteNoise(application, root=BASE_DIR / "staticfiles")

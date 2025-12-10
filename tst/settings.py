from pathlib import Path
import os

from django.contrib.messages import constants as messages
import dj_database_url
from dotenv import load_dotenv

ALLOWED_HOSTS = ["*"]

# BASE_DIR
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env (for local dev)
load_dotenv(BASE_DIR / ".env")

# -----------------------------
# Messaging tags (unchanged)
# -----------------------------
MESSAGE_TAGS = {
    messages.DEBUG: 'secondary',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',
}

# -----------------------------
# Security & debug
# -----------------------------

# SECRET_KEY from environment (Render + local .env)
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "dev-secret-key-change-me"  # fallback for local only
)

# DEBUG from environment (DJANGO_DEBUG="True" or "False")
DEBUG = os.environ.get("DJANGO_DEBUG", "True") == "True"

# -----------------------------
# Applications
# -----------------------------

INSTALLED_APPS = [
    'hiva',
    'dashboard',
    'product.apps.ProductConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'jalali_date_new',
    'django.contrib.postgres',
    'taggit',
    'kms.apps.KmsConfig',
]

# -----------------------------
# Middleware
# -----------------------------

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise for static files (important for Render)
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'tst.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # safer than plain 'templates'
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'tst.wsgi.application'

# -----------------------------
# Database
# -----------------------------
# Default: use DATABASE_URL if present (Render / .env)
# Fallback: your local Postgres connection

import os  # you already have this at the bottom; it's okay to have it once at the top

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        # Use environment variables if they exist (Render),
        # otherwise fall back to your current local settings.
        'NAME': os.environ.get('DB_NAME', 'pmp'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', '12345'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# -----------------------------
# Password validation
# -----------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# -----------------------------
# Internationalization
# -----------------------------

LANGUAGE_CODE = 'en-us'

# You might prefer Asia/Kabul for you:
TIME_ZONE = 'Asia/Kabul'

USE_I18N = True
USE_TZ = True

# -----------------------------
# Static & media files
# -----------------------------

STATIC_URL = '/static/'

# Folder where collectstatic will put files (for Render)
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Optional: if you have a local "static" folder in project root
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# WhiteNoise: compressed static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# -----------------------------
# Email settings (from environment / .env)
# -----------------------------

EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True") == "True"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))

# -----------------------------
# Default primary key field type
# -----------------------------

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

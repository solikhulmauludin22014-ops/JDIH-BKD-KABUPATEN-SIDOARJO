"""
Django settings for jdih_sidoarjo project.
Configured for BKD Kabupaten Sidoarjo JDIH Portal and Vercel Serverless.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file if present
load_dotenv(BASE_DIR / '.env')

# Quick-start development settings - unsuitable for production
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-jdih-bkd-sidoarjo-prod-change-key-998877665544'
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 't')

# ALLOWED_HOSTS for local and Vercel environments
allowed_hosts_env = os.environ.get('ALLOWED_HOSTS', '')
if allowed_hosts_env:
    ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_env.split(',') if host.strip()]
else:
    ALLOWED_HOSTS = ['*']

# Ensure localhost, testserver, and vercel are always permitted if not wildcard
if '*' not in ALLOWED_HOSTS:
    for default_host in ['localhost', '127.0.0.1', 'testserver', '.vercel.app']:
        if default_host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(default_host)

# CSRF Trusted Origins for Vercel and local
CSRF_TRUSTED_ORIGINS = [
    'https://*.vercel.app',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

# Application definition
INSTALLED_APPS = [
    'django.contrib.staticfiles',
    'django.contrib.messages',
    'django.contrib.sessions',
    
    # Project apps
    'core',
    'documents',
    'admin_panel',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'jdih_sidoarjo.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.institution_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'jdih_sidoarjo.wsgi.application'

# Database definition
# In accordance with project specs: SQLite is purely optional/fallback for local dev.
# Document data is stored in Firestore (NoSQL), Admin auth is handled by Firebase Auth.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ==============================================================================
# VERCEL SERVERLESS SESSIONS
# Signed Cookies session engine: No persistent database or server disk required!
# ==============================================================================
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
SESSION_COOKIE_NAME = 'jdih_bkd_sessionid'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 86400 * 7  # 7 days
SESSION_SAVE_EVERY_REQUEST = True

# Internationalization
LANGUAGE_CODE = 'id'
TIME_ZONE = 'Asia/Jakarta'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise storage configuration
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Allow iframe embedding for PDF viewer
X_FRAME_OPTIONS = 'SAMEORIGIN'

# ==============================================================================
# FIREBASE CREDENTIALS CONFIGURATION
# ==============================================================================
FIREBASE_PROJECT_ID = os.environ.get('FIREBASE_PROJECT_ID', 'jdih-bkd-sidoarjo')
FIREBASE_STORAGE_BUCKET = os.environ.get('FIREBASE_STORAGE_BUCKET', 'jdih-bkd-sidoarjo.firebasestorage.app')
FIREBASE_SERVICE_ACCOUNT_JSON = os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON')
FIREBASE_CREDENTIALS_PATH = os.environ.get('FIREBASE_CREDENTIALS_PATH', str(BASE_DIR / 'serviceAccountKey.json'))

# Firebase Client Web Config (for Admin Login)
FIREBASE_WEB_API_KEY = os.environ.get('FIREBASE_WEB_API_KEY', '')
FIREBASE_AUTH_DOMAIN = os.environ.get('FIREBASE_AUTH_DOMAIN', '')
FIREBASE_APP_ID = os.environ.get('FIREBASE_APP_ID', '')

# le_postier/settings.py
"""
Django settings for le_postier project.
Configured for local media storage on Render persistent disk.
"""

import os
from pathlib import Path
from decouple import config
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-8d0)r5bhf(r85cg*u_vbk-@k&i1bv%lvjah^34!siis!o1dekn')

DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.MediaServeMiddleware',
]

ROOT_URLCONF = 'le_postier.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
            ],
        },
    },
]

WSGI_APPLICATION = 'le_postier.wsgi.application'

# Database
DATABASE_URL = config('DATABASE_URL', default='postgresql://zzcorp:erc5uvp74IqqUFotZeQKT8BHAiMFxOOC@dpg-d51jlth5pdvs73e9m95g-a/z_data_db_zyx_u82e')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Custom User Model
AUTH_USER_MODEL = 'core.CustomUser'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# =============================================================================
# MEDIA FILES - LOCAL STORAGE ON RENDER PERSISTENT DISK
# =============================================================================
MEDIA_URL = '/media/'

# On Render, use the mounted persistent disk path
# Set via environment variable: MEDIA_ROOT=/var/data/media
# Locally, defaults to BASE_DIR / 'media'
MEDIA_ROOT = Path(config('MEDIA_ROOT', default=str(BASE_DIR / 'media')))

# Postcard image subdirectories
POSTCARD_IMAGE_DIRS = ['Vignette', 'Grande', 'Dos', 'Zoom']
ANIMATED_CP_DIR = 'animated_cp'
SIGNATURES_DIR = 'signatures'


def create_media_dirs():
    """Create media directories if they don't exist."""
    try:
        # Only create if MEDIA_ROOT exists (i.e., disk is mounted)
        if MEDIA_ROOT.exists() or str(MEDIA_ROOT).startswith('/var/data'):
            # Check if parent exists first
            if not MEDIA_ROOT.parent.exists():
                print(
                    f"Media root parent {MEDIA_ROOT.parent} does not exist - skipping directory creation (build phase)")
                return

            # Create postcard directories
            for subdir in POSTCARD_IMAGE_DIRS:
                (MEDIA_ROOT / 'postcards' / subdir).mkdir(parents=True, exist_ok=True)
            # Create animated postcards directory
            (MEDIA_ROOT / ANIMATED_CP_DIR).mkdir(parents=True, exist_ok=True)
            # Create signatures directory
            (MEDIA_ROOT / SIGNATURES_DIR).mkdir(parents=True, exist_ok=True)
            print(f"Media directories created/verified at: {MEDIA_ROOT}")
    except OSError as e:
        if "Read-only file system" in str(e):
            print(f"Skipping media directory creation (build phase - disk not mounted yet)")
        else:
            print(f"Warning: Could not create media directories: {e}")
    except Exception as e:
        print(f"Warning: Could not create media directories: {e}")


# Only try to create directories if not in build phase
import os

if os.environ.get('RENDER') != 'true' or os.path.exists('/var/data'):
    create_media_dirs()

# =============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login/Logout URLs
LOGIN_URL = '/connexion/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# CSRF Settings
CSRF_TRUSTED_ORIGINS = [
    'https://*.onrender.com',
    'https://collections.samathey.fr',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

# Security Settings for Production
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
else:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'core': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024  # 100 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024  # 100 MB
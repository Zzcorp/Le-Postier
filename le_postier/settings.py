# le_postier/settings.py
"""
Django settings for le_postier — single, environment-driven configuration.

Every deployment-specific value comes from the environment (read via
python-decouple, i.e. a `.env` file or real env vars). There is no separate
production settings module: production simply sets DEBUG=False and provides
real values in `.env`. See `.env.example` for the full list of variables and
`DEPLOY_OVH.md` for the production runbook.
"""

from pathlib import Path

import dj_database_url
from decouple import Csv, config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# =============================================================================
# CORE
# =============================================================================

# SECRET_KEY is REQUIRED — no default on purpose. Generate one with:
#   python -c "import secrets; print(secrets.token_urlsafe(50))"
# Rotating it invalidates all sessions and pending verification tokens.
SECRET_KEY = config('SECRET_KEY')

DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='collections.samathey.fr', cast=Csv())

# Absolute base URL of the site (no trailing slash) — used for sitemap/robots
# and absolute links in emails.
SITE_URL = config('SITE_URL', default='https://collections.samathey.fr')

CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='https://collections.samathey.fr',
    cast=Csv(),
)

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
    'core.middleware.AnalyticsTrackingMiddleware',
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

# =============================================================================
# DATABASE
# =============================================================================
# DATABASE_URL empty → local SQLite. In production, a postgres:// URL pointing
# at the compose `db` service (see docker-compose.yml / DEPLOY_OVH.md).
DATABASE_URL = config('DATABASE_URL', default='')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600),
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

# =============================================================================
# INTERNATIONALIZATION
# =============================================================================
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_TZ = True

# =============================================================================
# STATIC & MEDIA FILES
# =============================================================================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Django 5.2: STATICFILES_STORAGE was removed — storage backends are declared
# via the STORAGES dict. WhiteNoise serves hashed+compressed static files.
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

MEDIA_URL = '/media/'
# In production (compose) MEDIA_ROOT=/data/media, bind-mounted from
# /srv/lepostier/media on the host; nginx serves /media/ directly from the
# same bind mount. Locally it defaults to <project>/media — an EMPTY value in
# .env means "unset" too (the `or` below), matching .env.example's promise.
MEDIA_ROOT = Path(config('MEDIA_ROOT', default='') or (BASE_DIR / 'media'))

# =============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login/Logout URLs
LOGIN_URL = '/connexion/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# =============================================================================
# SECURITY (production — nginx terminates TLS in front of gunicorn)
# =============================================================================
# nginx sets X-Forwarded-Proto; without this, SECURE_SSL_REDIRECT would loop.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    # HSTS: start conservative (1 hour). Once HTTPS has run without issues for
    # a while, raise to 31536000 (1 year) and consider
    # SECURE_HSTS_INCLUDE_SUBDOMAINS / SECURE_HSTS_PRELOAD — a long max-age
    # with a broken TLS setup locks visitors out until it expires.
    SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=3600, cast=int)
else:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

# =============================================================================
# CACHE
# =============================================================================
# Local-memory cache: per-process, no external service. Used for IP-geolocation
# results and the heavy admin statistics endpoints (5-minute cache).
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'le-postier',
    }
}

# =============================================================================
# LOGGING — console only (docker/gunicorn capture stdout)
# =============================================================================
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
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# =============================================================================
# FILE UPLOADS
# =============================================================================
# 10 MB in-memory threshold: Django streams anything larger to a temp file on
# disk, so big admin video uploads never sit in RAM. The real upload size cap
# is nginx (`client_max_body_size 200m` in deploy/nginx.conf).
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB (non-file form data)

# =============================================================================
# EMAIL — Hostinger SMTP (password comes from the environment only)
# =============================================================================
EMAIL_BACKEND = config(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.smtp.EmailBackend',
)

EMAIL_HOST = config('EMAIL_HOST', default='smtp.hostinger.com')
EMAIL_PORT = config('EMAIL_PORT', default=465, cast=int)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=True, cast=bool)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=False, cast=bool)

EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='no-reply@collection-samathey.com')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

DEFAULT_FROM_EMAIL = config(
    'DEFAULT_FROM_EMAIL',
    default='Le Postier <no-reply@collection-samathey.com>',
)
SERVER_EMAIL = config('SERVER_EMAIL', default='no-reply@collection-samathey.com')

# Recipients of the contact form and admin notifications.
ADMIN_EMAILS = config(
    'ADMIN_EMAILS',
    default='sam@samathey.com,s.mathey@z-data.fr',
    cast=Csv(),
)

EMAIL_SUBJECT_PREFIX = '[Le Postier] '
EMAIL_TIMEOUT = 30

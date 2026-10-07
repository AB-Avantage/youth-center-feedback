import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get("FEEDBACK_SECRET_KEY", "local-development-only-change-before-deployment")
DEBUG = os.environ.get("FEEDBACK_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = [host.strip() for host in os.environ.get("FEEDBACK_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if host.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "feedback",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
        "feedback.context_processors.portal_copy",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"

# This database belongs only to the feedback application.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "feedback.sqlite3",
    }
}

# EZYXS is a read-only source of facilities and customer profiles. In production,
# give the MySQL user SELECT permission only on the three tables used below.
ezyxs_engine = os.environ.get("EZYXS_DB_ENGINE", "sqlite").lower()
if ezyxs_engine == "mysql":
    DATABASES["ezyxs"] = {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ.get("EZYXS_DB_NAME", "ezyxs"),
        "USER": os.environ.get("EZYXS_DB_USER", ""),
        "PASSWORD": os.environ.get("EZYXS_DB_PASSWORD", ""),
        "HOST": os.environ.get("EZYXS_DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("EZYXS_DB_PORT", "3306"),
        "OPTIONS": {"charset": "utf8mb4"},
    }
else:
    source_path = Path(os.environ.get("EZYXS_SQLITE_PATH", BASE_DIR.parent / "ezyxs-backend" / "db.sqlite3")).resolve()
    DATABASES["ezyxs"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": f"file:{source_path.as_posix()}?mode=ro",
        "OPTIONS": {"uri": True},
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
]
LANGUAGE_CODE = "en"
LANGUAGES = [("en", "English"), ("ar", "Arabic")]
TIME_ZONE = "Africa/Cairo"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "/staff/login/"

# Console delivery is for local development. Configure SMTP for real OTP emails.
EMAIL_BACKEND = os.environ.get("FEEDBACK_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.environ.get("FEEDBACK_EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("FEEDBACK_EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("FEEDBACK_EMAIL_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("FEEDBACK_EMAIL_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("FEEDBACK_EMAIL_USE_TLS", "true").lower() == "true"
DEFAULT_FROM_EMAIL = os.environ.get("FEEDBACK_FROM_EMAIL", "no-reply@example.com")

if not DEBUG and SECRET_KEY == "local-development-only-change-before-deployment":
    raise RuntimeError("Set FEEDBACK_SECRET_KEY before deployment")
if not DEBUG and EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend":
    raise RuntimeError("Configure FEEDBACK_EMAIL_BACKEND for real password reset emails")

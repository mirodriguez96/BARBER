import os

from .base import *  # noqa: F401,F403

DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() in ("true", "1", "yes")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "insecure-dev-key")

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

CSRF_TRUSTED_ORIGINS = os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")

DATABASES["default"].update({
    "HOST": os.environ.get("DB_HOST", "db"),
    "PORT": os.environ.get("DB_PORT", "5432"),
    "USER": os.environ.get("DB_USER", "barber_app"),
    "PASSWORD": os.environ.get("DB_PASSWORD", ""),
})

STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
if DEBUG:
    STORAGES["staticfiles"]["BACKEND"] = "whitenoise.storage.CompressedStaticFilesStorage"

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

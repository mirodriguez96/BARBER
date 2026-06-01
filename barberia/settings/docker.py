import os

from .base import *  # noqa: F401,F403

DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() in ("true", "1", "yes")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "insecure-dev-key")

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

CSRF_TRUSTED_ORIGINS = [
    o for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o
]

DATABASES["default"].update(
    {
        "HOST": os.environ.get("DB_HOST", "db"),
        "PORT": os.environ.get("DB_PORT", "5432"),
        "USER": os.environ.get("DB_USER", "barber_app"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
    }
)

STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
if DEBUG:
    STORAGES["staticfiles"][
        "BACKEND"
    ] = "whitenoise.storage.CompressedStaticFilesStorage"

if not DEBUG:
    SECURE_SSL_REDIRECT = os.environ.get(
        "DJANGO_SECURE_SSL_REDIRECT", "True"
    ).lower() in ("true", "1", "yes")
    SESSION_COOKIE_SECURE = os.environ.get(
        "DJANGO_SESSION_COOKIE_SECURE", "True"
    ).lower() in ("true", "1", "yes")
    CSRF_COOKIE_SECURE = os.environ.get(
        "DJANGO_CSRF_COOKIE_SECURE", "True"
    ).lower() in ("true", "1", "yes")
    SESSION_COOKIE_SAMESITE = os.environ.get("DJANGO_SESSION_COOKIE_SAMESITE", "Lax")
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get(
        "DJANGO_HSTS_INCLUDE_SUBDOMAINS", "True"
    ).lower() in ("true", "1", "yes")
    SECURE_HSTS_PRELOAD = os.environ.get("DJANGO_HSTS_PRELOAD", "True").lower() in (
        "true",
        "1",
        "yes",
    )

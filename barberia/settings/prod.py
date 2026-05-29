import os

from .base import *  # noqa: F401,F403

DEBUG = False

ALLOWED_HOSTS = [
    ".barbertech.com",
    "barbertech.com",
]

CSRF_TRUSTED_ORIGINS = [
    "https://*.barbertech.com",
    "https://barbertech.com",
]

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
    },
}

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "Lax"
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

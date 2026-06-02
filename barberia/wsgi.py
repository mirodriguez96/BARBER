"""WSGI config for barberia project."""

import os

from django.conf import settings
from django.core.wsgi import get_wsgi_application
from whitenoise import WhiteNoise

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "barberia.settings.dev")

application = get_wsgi_application()
application = WhiteNoise(application)
if hasattr(settings, "MEDIA_ROOT") and hasattr(settings, "MEDIA_URL"):
    application.add_files(settings.MEDIA_ROOT, prefix=settings.MEDIA_URL)

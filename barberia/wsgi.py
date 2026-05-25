"""WSGI config for barberia project."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "barberia.settings.dev")

application = get_wsgi_application()

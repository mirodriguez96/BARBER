import ipaddress

from django.conf import settings
from django.db import connections
from django.http import Http404

from barberia.routers import set_current_db_name
from barberia.tenants.models import Domain


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        raw_host = request.get_host()
        host = raw_host.split(":")[0]

        if not host or ".." in host or host.startswith("."):
            raise Http404("Host inválido")

        if self._is_public_host(host):
            set_current_db_name(None)
            return self.get_response(request)

        schema_name = self._extract_schema(host)
        if not schema_name:
            set_current_db_name(None)
            return self.get_response(request)

        try:
            domain = Domain.objects.select_related("tenant").get(
                domain__startswith=schema_name + ".",
            )
        except Domain.DoesNotExist:
            raise Http404("Barbería no encontrada")

        tenant = domain.tenant
        if not tenant.is_active:
            raise Http404("Barbería no activa")

        self._ensure_database(tenant.db_name)
        set_current_db_name(tenant.db_name)
        request.tenant = tenant

        response = self.get_response(request)
        set_current_db_name(None)
        return response

    def _is_public_host(self, host):
        public_prefixes = getattr(settings, "PUBLIC_HOST_PREFIXES", ["admin", "www"])
        if any(host.startswith(f"{p}.") for p in public_prefixes):
            return True
        if host in ("localhost", "127.0.0.1", "testserver"):
            return True
        try:
            ipaddress.ip_address(host)
            return True
        except ValueError:
            return False

    def _extract_schema(self, host):
        parts = host.split(".")
        if len(parts) >= 3:
            return parts[0]
        return None

    def _ensure_database(self, db_name):
        if db_name not in connections.databases:
            cfg = settings.DATABASES["default"]
            connections.databases[db_name] = {**cfg, "NAME": db_name}

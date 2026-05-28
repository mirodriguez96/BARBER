from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404
from django.shortcuts import render

from barberia.tenants.models import Tenant


def _is_public_host(host):
    prefixes = getattr(settings, "PUBLIC_HOST_PREFIXES", ["admin", "www"])
    if any(host.startswith(f"{p}.") for p in prefixes):
        return True
    return host in ("localhost", "127.0.0.1", "testserver")


@staff_member_required
def tenant_list(request):
    host = request.get_host().split(":")[0]
    if not _is_public_host(host):
        raise Http404("Panel solo accesible desde dominio público")
    tenants = Tenant.objects.all().order_by("-created_at")
    return render(request, "tenants/tenant_list.html", {"tenants": tenants})

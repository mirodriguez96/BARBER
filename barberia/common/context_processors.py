from barberia.common.models import Company
from barberia.tenants.models import Domain


def tenant_context(request):
    tenant = getattr(request, "tenant", None)
    if tenant is None:
        host = request.get_host().split(":")[0]
        try:
            domain = (
                Domain.objects.select_related("tenant")
                .filter(domain__iexact=host)
                .first()
            )
            if domain is not None:
                tenant = domain.tenant
        except Exception:
            tenant = None

    company_logo_url = ""
    try:
        company = Company.objects.exclude(logo="").first()
        if company and company.logo:
            company_logo_url = company.logo.url
    except Exception:
        company_logo_url = ""

    return {
        "tenant": tenant,
        "tenant_name": tenant.name if tenant else "Barbería",
        "tenant_schema": tenant.schema_name if tenant else "",
        "company_logo_url": company_logo_url,
    }

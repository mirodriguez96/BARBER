"""Tests for ``barberia.common.context_processors.tenant_context``.

Covers the multi-tenant resolution logic used by templates: when a request
arrives through ``TenantMiddleware`` (``request.tenant`` is set) the
processor uses it; otherwise it falls back to looking up the host in the
``Domain`` registry. The processor also exposes ``company_logo_url`` for
the sidebar/favicon.
"""

from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpRequest
from django.test import TestCase

from barberia.common.context_processors import tenant_context
from barberia.common.models import Company
from barberia.tenants.models import Domain, Tenant


def _png_file(name="logo.png", size=64):
    """Build a minimal in-memory PNG suitable for ``ImageField`` tests."""
    try:
        from PIL import Image
    except ImportError:  # pragma: no cover - Pillow always installed in this repo
        return SimpleUploadedFile(name, b"", content_type="image/png")
    buf = BytesIO()
    Image.new("RGB", (size, size), color="red").save(buf, format="PNG")
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type="image/png")


class TenantContextDefaultsTest(TestCase):
    """When no tenant is resolvable the processor must return safe defaults."""

    def test_returns_defaults_when_no_tenant_and_unknown_host(self):
        request = HttpRequest()
        request.META["HTTP_HOST"] = "ghost.example.com"
        ctx = tenant_context(request)
        self.assertIsNone(ctx["tenant"])
        self.assertEqual(ctx["tenant_name"], "Barbería")
        self.assertEqual(ctx["tenant_schema"], "")
        self.assertEqual(ctx["company_logo_url"], "")

    def test_does_not_raise_on_host_lookup_exception(self):
        request = HttpRequest()
        request.META["HTTP_HOST"] = "broken.example.com"

        class _BoomQueryset:
            def filter(self, *a, **kw):
                raise RuntimeError("db down")

        with __import__("unittest.mock", fromlist=["patch"]).patch(
            "barberia.common.context_processors.Domain.objects",
            new=_BoomQueryset(),
        ):
            ctx = tenant_context(request)
        self.assertIsNone(ctx["tenant"])
        self.assertEqual(ctx["tenant_name"], "Barbería")


class TenantContextFromRequestTenantTest(TestCase):
    """``TenantMiddleware`` sets ``request.tenant``; the processor must use it."""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            schema_name="luxor",
            db_name="barber_luxor",
            name="Luxor",
        )

    def test_uses_request_tenant_when_present(self):
        request = HttpRequest()
        request.META["HTTP_HOST"] = "anything.example.com"
        request.tenant = self.tenant
        ctx = tenant_context(request)
        self.assertIs(ctx["tenant"], self.tenant)
        self.assertEqual(ctx["tenant_name"], "Luxor")
        self.assertEqual(ctx["tenant_schema"], "luxor")


class TenantContextFromDomainFallbackTest(TestCase):
    """Falls back to ``Domain`` lookup when ``request.tenant`` is missing."""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            schema_name="prueba",
            db_name="barber_prueba",
            name="Prueba",
        )
        Domain.objects.create(domain="prueba.colstyle.com", tenant=self.tenant)

    def test_fallback_to_domain_lookup(self):
        request = HttpRequest()
        request.META["HTTP_HOST"] = "prueba.colstyle.com"
        ctx = tenant_context(request)
        self.assertEqual(ctx["tenant"], self.tenant)
        self.assertEqual(ctx["tenant_name"], "Prueba")
        self.assertEqual(ctx["tenant_schema"], "prueba")

    def test_strips_port_from_host(self):
        request = HttpRequest()
        request.META["HTTP_HOST"] = "prueba.colstyle.com:8000"
        ctx = tenant_context(request)
        self.assertEqual(ctx["tenant"], self.tenant)


class CompanyLogoUrlTest(TestCase):
    """``company_logo_url`` must surface the first Company with a non-empty logo."""

    def test_empty_when_no_company(self):
        request = HttpRequest()
        request.META["HTTP_HOST"] = "anything.example.com"
        ctx = tenant_context(request)
        self.assertEqual(ctx["company_logo_url"], "")

    def test_empty_when_company_has_no_logo(self):
        Company.objects.create(nit="1", name="Sin logo")
        request = HttpRequest()
        request.META["HTTP_HOST"] = "anything.example.com"
        ctx = tenant_context(request)
        self.assertEqual(ctx["company_logo_url"], "")

    def test_returns_logo_url_when_company_has_logo(self):
        company = Company.objects.create(nit="2", name="Con logo")
        company.logo.save("luxor.png", _png_file(), save=True)
        self.addCleanup(company.logo.delete, save=False)
        request = HttpRequest()
        request.META["HTTP_HOST"] = "anything.example.com"
        ctx = tenant_context(request)
        self.assertTrue(ctx["company_logo_url"].startswith("/media/"))
        self.assertIn("luxor", ctx["company_logo_url"])

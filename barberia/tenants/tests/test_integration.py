from unittest.mock import patch

from django.http import Http404, HttpRequest, HttpResponse
from django.test import TestCase, override_settings

from barberia.middleware import TenantMiddleware
from barberia.routers import get_current_db_name, set_current_db_name
from barberia.tenants.models import Domain, Tenant


@override_settings(ALLOWED_HOSTS=["*"])
class TenantMiddlewareIntegrationTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            schema_name="luxor",
            db_name="barber_luxor",
            name="Luxor Barbería",
            nit="1234567890",
        )
        self.domain = Domain.objects.create(
            domain="luxor.colstyle.com", tenant=self.tenant, is_primary=True
        )
        self.response = HttpResponse()
        set_current_db_name(None)

    def tearDown(self):
        set_current_db_name(None)

    def _make_request(self, host):
        request = HttpRequest()
        request.META["HTTP_HOST"] = host
        return request

    @patch("barberia.middleware.TenantMiddleware._ensure_database")
    def test_valid_domain_lookup(self, mock_ensure):
        mw = TenantMiddleware(get_response=lambda r: self.response)
        request = self._make_request("luxor.colstyle.com")
        response = mw(request)

        mock_ensure.assert_called_once_with("barber_luxor")
        self.assertEqual(request.tenant, self.tenant)
        self.assertIs(response, self.response)

    @patch("barberia.middleware.TenantMiddleware._ensure_database")
    def test_valid_domain_sets_and_clears_db(self, mock_ensure):
        mw = TenantMiddleware(get_response=lambda r: self.response)
        request = self._make_request("luxor.colstyle.com")
        mw(request)

        self.assertIsNone(get_current_db_name())

    @patch("barberia.middleware.TenantMiddleware._ensure_database")
    def test_valid_domain_multiple_tenants_isolation(self, mock_ensure):
        other_tenant = Tenant.objects.create(
            schema_name="stilo",
            db_name="barber_stilo",
            name="Stilo",
            nit="0987654321",
        )
        Domain.objects.create(
            domain="stilo.colstyle.com", tenant=other_tenant, is_primary=True
        )

        mw = TenantMiddleware(get_response=lambda r: self.response)
        request = self._make_request("stilo.colstyle.com")
        mw(request)

        self.assertEqual(request.tenant, other_tenant)
        self.assertEqual(request.tenant.schema_name, "stilo")

    def test_unknown_domain_404(self):
        mw = TenantMiddleware(get_response=lambda r: self.response)
        request = self._make_request("ghost.colstyle.com")
        with self.assertRaises(Http404):
            mw(request)

    def test_inactive_tenant_404(self):
        inactive = Tenant.objects.create(
            schema_name="old",
            db_name="barber_old",
            name="Old",
            is_active=False,
            nit="5555555555",
        )
        Domain.objects.create(
            domain="old.colstyle.com", tenant=inactive, is_primary=True
        )

        mw = TenantMiddleware(get_response=lambda r: self.response)
        request = self._make_request("old.colstyle.com")
        with self.assertRaises(Http404):
            mw(request)

    def test_double_dot_host_404(self):
        mw = TenantMiddleware(get_response=lambda r: self.response)
        request = self._make_request("a..b.com")
        with self.assertRaises(Http404):
            mw(request)

    def test_public_host_skips_db_lookup(self):
        mw = TenantMiddleware(get_response=lambda r: self.response)
        request = self._make_request("admin.colstyle.com")
        response = mw(request)
        self.assertIs(response, self.response)
        self.assertFalse(hasattr(request, "tenant"))

    def test_ip_address_skips_db_lookup(self):
        mw = TenantMiddleware(get_response=lambda r: self.response)
        request = self._make_request("66.23.224.249")
        response = mw(request)
        self.assertIs(response, self.response)
        self.assertFalse(hasattr(request, "tenant"))

    def test_extract_schema_with_subdomain(self):
        mw = TenantMiddleware(get_response=lambda r: self.response)
        self.assertEqual(mw._extract_schema("luxor.colstyle.com"), "luxor")

    def test_extract_schema_no_subdomain(self):
        mw = TenantMiddleware(get_response=lambda r: self.response)
        self.assertIsNone(mw._extract_schema("localhost"))

    @patch("barberia.middleware.TenantMiddleware._ensure_database")
    def test_multiple_tenants_independent_lookups(self, mock_ensure):
        t2 = Tenant.objects.create(
            schema_name="cortes",
            db_name="barber_cortes",
            name="Cortes",
            nit="9999999999",
        )
        Domain.objects.create(domain="cortes.colstyle.com", tenant=t2, is_primary=True)

        mw = TenantMiddleware(get_response=lambda r: self.response)

        request1 = self._make_request("luxor.colstyle.com")
        mw(request1)
        self.assertEqual(request1.tenant.schema_name, "luxor")

        request2 = self._make_request("cortes.colstyle.com")
        mw(request2)
        self.assertEqual(request2.tenant.schema_name, "cortes")

from unittest.mock import MagicMock, patch

from django.http import Http404, HttpRequest, HttpResponse
from django.test import TestCase, override_settings

from barberia.middleware import TenantMiddleware
from barberia.routers import get_current_db_name, set_current_db_name
from barberia.tenants.models import Domain


class _isPublicHostTest(TestCase):
    def setUp(self):
        self.mw = TenantMiddleware(get_response=lambda r: HttpResponse())

    def test_localhost(self):
        self.assertTrue(self.mw._is_public_host("localhost"))

    def test_127_0_0_1(self):
        self.assertTrue(self.mw._is_public_host("127.0.0.1"))

    def test_testserver(self):
        self.assertTrue(self.mw._is_public_host("testserver"))

    def test_admin_prefix(self):
        self.assertTrue(self.mw._is_public_host("admin.barberia.com"))

    def test_www_prefix(self):
        self.assertTrue(self.mw._is_public_host("www.barberia.com"))

    def test_tenant_subdomain(self):
        self.assertFalse(self.mw._is_public_host("luxor.barberia.com"))

    def test_deep_subdomain(self):
        self.assertFalse(self.mw._is_public_host("a.b.c.barberia.com"))


class _extractSchemaTest(TestCase):
    def setUp(self):
        self.mw = TenantMiddleware(get_response=lambda r: HttpResponse())

    def test_three_parts(self):
        self.assertEqual(self.mw._extract_schema("luxor.barberia.com"), "luxor")

    def test_three_parts_other_tld(self):
        self.assertEqual(self.mw._extract_schema("stilo.mibarberia.net"), "stilo")

    def test_two_parts(self):
        self.assertIsNone(self.mw._extract_schema("localhost"))

    def test_one_part(self):
        self.assertIsNone(self.mw._extract_schema("localhost"))


@override_settings(ALLOWED_HOSTS=["*"])
class TenantMiddlewareCallTest(TestCase):
    def setUp(self):
        self.response = HttpResponse()
        self.mw = TenantMiddleware(get_response=lambda r: self.response)
        set_current_db_name(None)

    def tearDown(self):
        set_current_db_name(None)

    def test_public_host_skips_lookup(self):
        request = HttpRequest()
        request.META["HTTP_HOST"] = "admin.barberia.com"
        response = self.mw(request)
        self.assertIs(response, self.response)
        self.assertIsNone(get_current_db_name())
        self.assertFalse(hasattr(request, "tenant"))

    def test_localhost_skips_lookup(self):
        request = HttpRequest()
        request.META["HTTP_HOST"] = "localhost"
        response = self.mw(request)
        self.assertIs(response, self.response)
        self.assertIsNone(get_current_db_name())

    @patch("barberia.middleware.Domain.objects")
    def test_unknown_domain_raises_404(self, mock_objects):
        mock_select = mock_objects.select_related.return_value
        mock_select.get.side_effect = Domain.DoesNotExist

        request = HttpRequest()
        request.META["HTTP_HOST"] = "ghost.barberia.com"
        with self.assertRaises(Http404):
            self.mw(request)

    @patch("barberia.middleware.Domain.objects")
    @patch("barberia.middleware.TenantMiddleware._ensure_database")
    def test_valid_domain_sets_tenant_and_db(self, mock_ensure, mock_objects):
        mock_tenant = MagicMock()
        mock_tenant.db_name = "barber_luxor"
        mock_tenant.is_active = True

        mock_domain = MagicMock()
        mock_domain.tenant = mock_tenant

        mock_select = mock_objects.select_related.return_value
        mock_select.get.return_value = mock_domain

        request = HttpRequest()
        request.META["HTTP_HOST"] = "luxor.barberia.com"
        response = self.mw(request)

        mock_ensure.assert_called_once_with("barber_luxor")
        self.assertEqual(request.tenant, mock_tenant)
        self.assertIs(response, self.response)
        self.assertIsNone(get_current_db_name())

    @patch("barberia.middleware.Domain.objects")
    def test_inactive_tenant_raises_404(self, mock_objects):
        mock_tenant = MagicMock()
        mock_tenant.is_active = False

        mock_domain = MagicMock()
        mock_domain.tenant = mock_tenant

        mock_select = mock_objects.select_related.return_value
        mock_select.get.return_value = mock_domain

        request = HttpRequest()
        request.META["HTTP_HOST"] = "deactivated.barberia.com"
        with self.assertRaises(Http404):
            self.mw(request)


@override_settings(PUBLIC_HOST_PREFIXES=["panel", "api"])
class PublicHostPrefixesOverrideTest(TestCase):
    def test_custom_prefixes(self):
        mw = TenantMiddleware(get_response=lambda r: HttpResponse())
        self.assertTrue(mw._is_public_host("panel.barberia.com"))
        self.assertTrue(mw._is_public_host("api.barberia.com"))
        self.assertFalse(mw._is_public_host("admin.barberia.com"))

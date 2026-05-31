from django.test import TestCase
from django.urls import reverse

from barberia.accounts.models import User
from barberia.dashboard.models import RoleMenuPermission


class PermissionEnforcementTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            password="pass1234",
            role=User.Role.ADMIN,
        )
        self.barbero = User.objects.create_user(
            username="barbero",
            password="pass1234",
            role=User.Role.BARBERO,
        )
        self.estilista = User.objects.create_user(
            username="estilista",
            password="pass1234",
            role=User.Role.ESTILISTA,
        )
        self.list_url = reverse("dashboard:home")

        RoleMenuPermission.objects.create(role=User.Role.BARBERO, menu_key="overview")
        RoleMenuPermission.objects.create(role=User.Role.BARBERO, menu_key="barbers")
        RoleMenuPermission.objects.create(role=User.Role.BARBERO, menu_key="catalog")
        RoleMenuPermission.objects.create(role=User.Role.BARBERO, menu_key="payments")
        RoleMenuPermission.objects.create(role=User.Role.BARBERO, menu_key="config")
        for key in ["overview", "barbers", "catalog", "payments", "config"]:
            RoleMenuPermission.objects.create(role=User.Role.ESTILISTA, menu_key=key)

    def _url(self, section):
        return f"{self.list_url}?section={section}"

    def _assert_allowed(self, client, section):
        response = client.get(self._url(section))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["active_section"], section)

    def _assert_redirected(self, client, section):
        response = client.get(self._url(section))
        self.assertRedirects(response, f"{self.list_url}?section=overview")

    # --- Barbero access ---

    def test_barbero_allowed_overview(self):
        self.client.login(username="barbero", password="pass1234")
        self._assert_allowed(self.client, "overview")

    def test_barbero_allowed_barbers(self):
        self.client.login(username="barbero", password="pass1234")
        self._assert_allowed(self.client, "barbers")

    def test_barbero_allowed_catalog(self):
        self.client.login(username="barbero", password="pass1234")
        self._assert_allowed(self.client, "catalog")

    def test_barbero_allowed_payments(self):
        self.client.login(username="barbero", password="pass1234")
        self._assert_allowed(self.client, "payments")

    def test_barbero_allowed_config(self):
        self.client.login(username="barbero", password="pass1234")
        self._assert_allowed(self.client, "config")

    def test_barbero_blocked_from_sales(self):
        self.client.login(username="barbero", password="pass1234")
        self._assert_redirected(self.client, "sales")

    def test_barbero_blocked_from_compras(self):
        self.client.login(username="barbero", password="pass1234")
        self._assert_redirected(self.client, "compras")

    def test_barbero_blocked_from_inventory(self):
        self.client.login(username="barbero", password="pass1234")
        self._assert_redirected(self.client, "inventory")

    # --- Estilista access ---

    def test_estilista_allowed_overview(self):
        self.client.login(username="estilista", password="pass1234")
        self._assert_allowed(self.client, "overview")

    def test_estilista_allowed_barbers(self):
        self.client.login(username="estilista", password="pass1234")
        self._assert_allowed(self.client, "barbers")

    def test_estilista_allowed_catalog(self):
        self.client.login(username="estilista", password="pass1234")
        self._assert_allowed(self.client, "catalog")

    def test_estilista_allowed_payments(self):
        self.client.login(username="estilista", password="pass1234")
        self._assert_allowed(self.client, "payments")

    def test_estilista_allowed_config(self):
        self.client.login(username="estilista", password="pass1234")
        self._assert_allowed(self.client, "config")

    def test_estilista_blocked_from_sales(self):
        self.client.login(username="estilista", password="pass1234")
        self._assert_redirected(self.client, "sales")

    def test_estilista_blocked_from_compras(self):
        self.client.login(username="estilista", password="pass1234")
        self._assert_redirected(self.client, "compras")

    def test_estilista_blocked_from_inventory(self):
        self.client.login(username="estilista", password="pass1234")
        self._assert_redirected(self.client, "inventory")

    # --- Admin always has access ---

    def test_admin_access_all_sections(self):
        self.client.login(username="admin", password="pass1234")
        for section in [
            "overview",
            "barbers",
            "catalog",
            "sales",
            "compras",
            "payments",
            "inventory",
            "config",
        ]:
            self._assert_allowed(self.client, section)

    # --- POST bypass protection ---

    def test_barbero_post_to_blocked_section_redirects(self):
        self.client.login(username="barbero", password="pass1234")
        response = self.client.post(
            self.list_url,
            {"section": "sales", "action": "list"},
        )
        self.assertRedirects(response, f"{self.list_url}?section=overview")

    def test_estilista_post_to_blocked_section_redirects(self):
        self.client.login(username="estilista", password="pass1234")
        response = self.client.post(
            self.list_url,
            {"section": "inventory", "action": "list"},
        )
        self.assertRedirects(response, f"{self.list_url}?section=overview")

    def test_admin_post_to_all_sections_ok(self):
        self.client.login(username="admin", password="pass1234")
        response = self.client.post(
            self.list_url,
            {"section": "sales", "action": "list"},
        )
        self.assertEqual(response.status_code, 200)


class PermissionEnforcementNoPermissionsTest(TestCase):
    """When no permissions exist for a role, overview stays accessible but other sections redirect."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="barbero",
            password="pass1234",
            role=User.Role.BARBERO,
        )
        self.list_url = reverse("dashboard:home")

    def test_no_permissions_overview_allowed(self):
        self.client.login(username="barbero", password="pass1234")
        response = self.client.get(f"{self.list_url}?section=overview")
        self.assertEqual(response.status_code, 200)

    def test_no_permissions_redirects_other_sections(self):
        self.client.login(username="barbero", password="pass1234")
        for section in [
            "barbers",
            "catalog",
            "sales",
            "compras",
            "payments",
            "inventory",
            "config",
        ]:
            response = self.client.get(f"{self.list_url}?section={section}")
            self.assertRedirects(
                response,
                f"{self.list_url}?section=overview",
                fetch_redirect_response=False,
            )

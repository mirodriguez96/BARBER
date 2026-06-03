from datetime import datetime

from django.test import TestCase
from django.urls import reverse

from barberia.accounts.models import User
from barberia.catalog.models import CatalogItem
from barberia.dashboard.models import RoleCrudPermission, RoleMenuPermission
from barberia.operations.models import Purchase, Sale
from barberia.people.models import Client, Employee


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


class CrudPersonalPermissionTest(TestCase):
    """CRUD permission enforcement for app_key='personal' (barbers section)."""

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

        self.barber = Employee.objects.create(
            full_name="Test Barber",
            document_id="DOC001",
            phone="123456789",
        )
        self.client_person = Client.objects.create(
            full_name="Test Client",
            document_id="DOC002",
            phone="987654321",
        )

        RoleMenuPermission.objects.create(role=User.Role.BARBERO, menu_key="barbers")
        RoleMenuPermission.objects.create(role=User.Role.ESTILISTA, menu_key="barbers")

    def _url(self, section, view="list", **kwargs):
        url = f"{self.list_url}?section={section}&view={view}"
        for k, v in kwargs.items():
            url += f"&{k}={v}"
        return url

    # ── Context ──

    def test_context_without_permissions(self):
        self.client.login(username="barbero", password="pass1234")
        response = self.client.get(self._url("barbers"))
        self.assertFalse(response.context["can_register_personal"])
        self.assertFalse(response.context["can_modify_personal"])
        self.assertFalse(response.context["can_deactivate_personal"])

    def test_context_with_all_permissions(self):
        for action in ("registrar", "modificar", "desactivar"):
            RoleCrudPermission.objects.create(
                role=User.Role.BARBERO,
                app_key=RoleCrudPermission.AppKey.PERSONAL,
                action=action,
            )
        self.client.login(username="barbero", password="pass1234")
        response = self.client.get(self._url("barbers"))
        self.assertTrue(response.context["can_register_personal"])
        self.assertTrue(response.context["can_modify_personal"])
        self.assertTrue(response.context["can_deactivate_personal"])

    def test_context_admin_always_true(self):
        self.client.login(username="admin", password="pass1234")
        response = self.client.get(self._url("barbers"))
        self.assertTrue(response.context["can_register_personal"])
        self.assertTrue(response.context["can_modify_personal"])
        self.assertTrue(response.context["can_deactivate_personal"])

    # ── POST: deactivate ──

    def test_deactivate_barber_without_permission(self):
        self.client.login(username="barbero", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "barbers",
                "action": "deactivate",
                "barber_id": self.barber.pk,
            },
        )
        self.assertRedirects(response, self._url("barbers"))
        self.barber.refresh_from_db()
        self.assertTrue(self.barber.is_active)

    def test_deactivate_barber_with_permission(self):
        RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key=RoleCrudPermission.AppKey.PERSONAL,
            action="desactivar",
        )
        self.client.login(username="barbero", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "barbers",
                "action": "deactivate",
                "barber_id": self.barber.pk,
            },
        )
        self.assertRedirects(response, self._url("barbers"))
        self.barber.refresh_from_db()
        self.assertFalse(self.barber.is_active)

    # ── POST: activate ──

    def test_activate_barber_without_permission(self):
        self.barber.is_active = False
        self.barber.save()
        self.client.login(username="barbero", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "barbers",
                "action": "activate",
                "barber_id": self.barber.pk,
            },
        )
        self.assertRedirects(response, self._url("barbers"))
        self.barber.refresh_from_db()
        self.assertFalse(self.barber.is_active)

    def test_activate_barber_with_permission(self):
        self.barber.is_active = False
        self.barber.save()
        RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key=RoleCrudPermission.AppKey.PERSONAL,
            action="desactivar",
        )
        self.client.login(username="barbero", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "barbers",
                "action": "activate",
                "barber_id": self.barber.pk,
            },
        )
        self.assertRedirects(response, self._url("barbers"))
        self.barber.refresh_from_db()
        self.assertTrue(self.barber.is_active)

    # ── POST: update barber ──

    def test_update_barber_without_permission(self):
        self.client.login(username="barbero", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "barbers",
                "action": "update",
                "barber_id": self.barber.pk,
                "full_name": "Hacked",
                "document_id": "DOC001",
                "phone": "000000000",
            },
        )
        self.assertRedirects(response, self._url("barbers"))
        self.barber.refresh_from_db()
        self.assertEqual(self.barber.full_name, "Test Barber")

    def test_update_barber_with_permission(self):
        RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key=RoleCrudPermission.AppKey.PERSONAL,
            action="modificar",
        )
        self.client.login(username="barbero", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "barbers",
                "action": "update",
                "barber_id": self.barber.pk,
                "full_name": "Updated",
                "phone": "000000000",
                "email": "",
                "role": User.Role.BARBERO,
            },
        )
        self.assertRedirects(response, self._url("barbers"))
        self.barber.refresh_from_db()
        self.assertEqual(self.barber.full_name, "Updated")

    # ── POST: deactivate client ──

    def test_deactivate_client_without_permission(self):
        self.client.login(username="barbero", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "barbers",
                "action": "deactivate",
                "client_id": self.client_person.pk,
            },
        )
        self.assertRedirects(response, self._url("barbers"))
        self.client_person.refresh_from_db()
        self.assertTrue(self.client_person.is_active)

    def test_deactivate_client_with_permission(self):
        RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key=RoleCrudPermission.AppKey.PERSONAL,
            action="desactivar",
        )
        self.client.login(username="barbero", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "barbers",
                "action": "deactivate",
                "client_id": self.client_person.pk,
            },
        )
        self.assertRedirects(response, self._url("barbers"))
        self.client_person.refresh_from_db()
        self.assertFalse(self.client_person.is_active)

    # ── POST: activate client ──

    def test_activate_client_without_permission(self):
        self.client_person.is_active = False
        self.client_person.save()
        self.client.login(username="barbero", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "barbers",
                "action": "activate",
                "client_id": self.client_person.pk,
            },
        )
        self.assertRedirects(response, self._url("barbers"))
        self.client_person.refresh_from_db()
        self.assertFalse(self.client_person.is_active)

    def test_activate_client_with_permission(self):
        self.client_person.is_active = False
        self.client_person.save()
        RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key=RoleCrudPermission.AppKey.PERSONAL,
            action="desactivar",
        )
        self.client.login(username="barbero", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "barbers",
                "action": "activate",
                "client_id": self.client_person.pk,
            },
        )
        self.assertRedirects(response, self._url("barbers"))
        self.client_person.refresh_from_db()
        self.assertTrue(self.client_person.is_active)

    # ── POST: update client ──

    def test_update_client_without_permission(self):
        self.client.login(username="barbero", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "barbers",
                "action": "update",
                "client_id": self.client_person.pk,
                "full_name": "Hacked",
                "document_id": "DOC002",
                "phone": "000000000",
            },
        )
        self.assertRedirects(response, self._url("barbers"))
        self.client_person.refresh_from_db()
        self.assertEqual(self.client_person.full_name, "Test Client")

    def test_update_client_with_permission(self):
        RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key=RoleCrudPermission.AppKey.PERSONAL,
            action="modificar",
        )
        self.client.login(username="barbero", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "barbers",
                "action": "update",
                "client_id": self.client_person.pk,
                "full_name": "Updated",
                "document_id": "DOC002",
                "phone": "000000000",
            },
        )
        self.assertRedirects(response, self._url("barbers"))
        self.client_person.refresh_from_db()
        self.assertEqual(self.client_person.full_name, "Updated")

    # ── GET form (registrar) ──

    def test_get_form_without_register_permission(self):
        self.client.login(username="barbero", password="pass1234")
        response = self.client.get(self._url("barbers", view="form"))
        self.assertRedirects(response, self._url("barbers"))

    def test_get_form_with_register_permission(self):
        RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key=RoleCrudPermission.AppKey.PERSONAL,
            action="registrar",
        )
        self.client.login(username="barbero", password="pass1234")
        response = self.client.get(self._url("barbers", view="form"))
        self.assertEqual(response.status_code, 200)

    # ── GET edit (modificar) ──

    def test_get_edit_barber_without_modify_permission(self):
        self.client.login(username="barbero", password="pass1234")
        response = self.client.get(
            self._url("barbers", view="edit", barber=self.barber.pk)
        )
        self.assertRedirects(response, self._url("barbers"))

    def test_get_edit_barber_with_modify_permission(self):
        RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key=RoleCrudPermission.AppKey.PERSONAL,
            action="modificar",
        )
        self.client.login(username="barbero", password="pass1234")
        response = self.client.get(
            self._url("barbers", view="edit", barber=self.barber.pk)
        )
        self.assertEqual(response.status_code, 200)

    def test_get_edit_client_without_modify_permission(self):
        self.client.login(username="barbero", password="pass1234")
        response = self.client.get(
            self._url("barbers", view="edit", client=self.client_person.pk)
        )
        self.assertRedirects(response, self._url("barbers"))

    def test_get_edit_client_with_modify_permission(self):
        RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key=RoleCrudPermission.AppKey.PERSONAL,
            action="modificar",
        )
        self.client.login(username="barbero", password="pass1234")
        response = self.client.get(
            self._url("barbers", view="edit", client=self.client_person.pk)
        )
        self.assertEqual(response.status_code, 200)

    # ── Admin bypass ──

    def test_admin_bypasses_crud_checks(self):
        self.client.login(username="admin", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "barbers",
                "action": "deactivate",
                "barber_id": self.barber.pk,
            },
        )
        self.assertRedirects(response, self._url("barbers"))
        self.barber.refresh_from_db()
        self.assertFalse(self.barber.is_active)

    def test_admin_register_form_always_accessible(self):
        self.client.login(username="admin", password="pass1234")
        response = self.client.get(self._url("barbers", view="form"))
        self.assertEqual(response.status_code, 200)

    def test_admin_edit_always_accessible(self):
        self.client.login(username="admin", password="pass1234")
        response = self.client.get(
            self._url("barbers", view="edit", barber=self.barber.pk)
        )
        self.assertEqual(response.status_code, 200)

    # ── Estilista blocked (no crud permissions created) ──

    def test_estilista_blocked_all_crud_actions(self):
        self.client.login(username="estilista", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "barbers",
                "action": "deactivate",
                "barber_id": self.barber.pk,
            },
        )
        self.assertRedirects(response, self._url("barbers"))
        self.barber.refresh_from_db()
        self.assertTrue(self.barber.is_active)  # unchanged


class CrudVentasPermissionTest(TestCase):
    """CRUD permission enforcement for app_key='ventas' (sales section)."""

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

        self.employee = Employee.objects.create(
            full_name="Barbero Emp",
            document_id="DOC001",
            phone="123456789",
            user=self.barbero,
        )
        self.catalog_item = CatalogItem.objects.create(
            name="Corte",
            kind=CatalogItem.Kind.SERVICE,
            price=25000,
        )
        self.sale = Sale.objects.create(
            product=self.catalog_item,
            employee=self.employee,
            performed_by=self.barbero,
            scheduled_for=datetime(2026, 5, 30, 10, 0),
            product_price=25000,
            status=Sale.Status.DONE,
        )

        RoleMenuPermission.objects.create(role=User.Role.BARBERO, menu_key="sales")
        RoleMenuPermission.objects.create(role=User.Role.ESTILISTA, menu_key="sales")

    def _url(self, section, view="list", **kwargs):
        url = f"{self.list_url}?section={section}&view={view}"
        for k, v in kwargs.items():
            url += f"&{k}={v}"
        return url

    # ── Context ──

    def test_context_without_permissions(self):
        self.client.login(username="barbero", password="pass1234")
        response = self.client.get(self._url("sales"))
        self.assertFalse(response.context["can_register_ventas"])
        self.assertFalse(response.context["can_modify_ventas"])
        self.assertFalse(response.context["can_deactivate_ventas"])

    def test_context_with_all_permissions(self):
        for action in ("registrar", "modificar", "desactivar"):
            RoleCrudPermission.objects.create(
                role=User.Role.BARBERO,
                app_key=RoleCrudPermission.AppKey.VENTAS,
                action=action,
            )
        self.client.login(username="barbero", password="pass1234")
        response = self.client.get(self._url("sales"))
        self.assertTrue(response.context["can_register_ventas"])
        self.assertTrue(response.context["can_modify_ventas"])
        self.assertTrue(response.context["can_deactivate_ventas"])

    def test_context_admin_always_true(self):
        self.client.login(username="admin", password="pass1234")
        response = self.client.get(self._url("sales"))
        self.assertTrue(response.context["can_register_ventas"])
        self.assertTrue(response.context["can_modify_ventas"])
        self.assertTrue(response.context["can_deactivate_ventas"])

    # ── POST: create ──

    def test_create_sale_without_permission(self):
        self.client.login(username="barbero", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "sales",
            },
        )
        self.assertRedirects(response, self._url("sales"))

    def test_create_sale_with_permission(self):
        RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key=RoleCrudPermission.AppKey.VENTAS,
            action="registrar",
        )
        self.client.login(username="barbero", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "sales",
                "employee": str(self.employee.pk),
                "product": str(self.catalog_item.pk),
                "client": "",
                "scheduled_for": "2026-05-30T10:00",
                "notes": "",
                "tip_amount": "",
            },
        )
        self.assertRedirects(response, f"{self.list_url}?section=sales")

    # ── POST: update ──

    def test_update_sale_without_permission(self):
        self.client.login(username="barbero", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "sales",
                "action": "update",
                "sale_id": str(self.sale.pk),
                "employee": str(self.employee.pk),
                "product": str(self.catalog_item.pk),
                "tip_amount": "0",
            },
        )
        self.assertRedirects(response, self._url("sales"))
        self.sale.refresh_from_db()
        self.assertEqual(self.sale.status, Sale.Status.DONE)

    def test_update_sale_with_permission(self):
        RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key=RoleCrudPermission.AppKey.VENTAS,
            action="modificar",
        )
        self.client.login(username="barbero", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "sales",
                "action": "update",
                "sale_id": str(self.sale.pk),
                "employee": str(self.employee.pk),
                "product": str(self.catalog_item.pk),
                "tip_amount": "5000",
            },
        )
        self.assertRedirects(response, self._url("sales"))
        self.sale.refresh_from_db()
        self.assertEqual(self.sale.tip_amount, 5000)

    # ── POST: cancel ──

    def test_cancel_sale_without_permission(self):
        self.client.login(username="barbero", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "sales",
                "action": "cancel",
                "sale_id": str(self.sale.pk),
            },
        )
        self.assertRedirects(response, self._url("sales"))
        self.sale.refresh_from_db()
        self.assertEqual(self.sale.status, Sale.Status.DONE)

    def test_cancel_sale_with_permission(self):
        RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key=RoleCrudPermission.AppKey.VENTAS,
            action="desactivar",
        )
        self.client.login(username="barbero", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "sales",
                "action": "cancel",
                "sale_id": str(self.sale.pk),
            },
        )
        self.assertRedirects(response, self._url("sales"))
        self.sale.refresh_from_db()
        self.assertEqual(self.sale.status, Sale.Status.CANCELED)

    # ── GET form (registrar) ──

    def test_get_form_without_register_permission(self):
        self.client.login(username="barbero", password="pass1234")
        response = self.client.get(self._url("sales", view="form"))
        self.assertRedirects(response, self._url("sales"))

    def test_get_form_with_register_permission(self):
        RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key=RoleCrudPermission.AppKey.VENTAS,
            action="registrar",
        )
        self.client.login(username="barbero", password="pass1234")
        response = self.client.get(self._url("sales", view="form"))
        self.assertEqual(response.status_code, 200)

    # ── GET edit (modificar) ──

    def test_get_edit_without_modify_permission(self):
        self.client.login(username="barbero", password="pass1234")
        response = self.client.get(self._url("sales", view="edit", sale=self.sale.pk))
        self.assertRedirects(response, self._url("sales"))

    def test_get_edit_with_modify_permission(self):
        RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key=RoleCrudPermission.AppKey.VENTAS,
            action="modificar",
        )
        self.client.login(username="barbero", password="pass1234")
        response = self.client.get(self._url("sales", view="edit", sale=self.sale.pk))
        self.assertEqual(response.status_code, 200)

    # ── Admin bypass ──

    def test_admin_bypasses_crud_checks(self):
        self.client.login(username="admin", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "sales",
                "action": "cancel",
                "sale_id": str(self.sale.pk),
            },
        )
        self.assertRedirects(response, self._url("sales"))
        self.sale.refresh_from_db()
        self.assertEqual(self.sale.status, Sale.Status.CANCELED)

    # ── Estilista blocked (no crud permissions created) ──

    def test_estilista_blocked_all_crud_actions(self):
        self.client.login(username="estilista", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "sales",
                "action": "cancel",
                "sale_id": str(self.sale.pk),
            },
        )
        self.assertRedirects(response, self._url("sales"))
        self.sale.refresh_from_db()
        self.assertEqual(self.sale.status, Sale.Status.DONE)


class CrudComprasPermissionTest(TestCase):
    """CRUD permission enforcement for app_key='compras' (purchases section)."""

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

        self.product = CatalogItem.objects.create(
            name="Test Product",
            kind=CatalogItem.Kind.PRODUCT,
            price=10000,
            current_stock=50,
        )
        self.purchase = Purchase.objects.create(
            product=self.product,
            quantity=10,
            unit_cost=5000,
            created_by=self.barbero,
            notes="Test purchase",
        )

        RoleMenuPermission.objects.create(role=User.Role.BARBERO, menu_key="compras")
        RoleMenuPermission.objects.create(role=User.Role.ESTILISTA, menu_key="compras")

    def _url(self, section, view="list", **kwargs):
        url = f"{self.list_url}?section={section}&view={view}"
        for k, v in kwargs.items():
            url += f"&{k}={v}"
        return url

    # ── Context ──

    def test_context_without_permissions(self):
        self.client.login(username="barbero", password="pass1234")
        response = self.client.get(self._url("compras"))
        self.assertFalse(response.context["can_register_compras"])
        self.assertFalse(response.context["can_modify_compras"])
        self.assertFalse(response.context["can_deactivate_compras"])

    def test_context_with_all_permissions(self):
        for action in ("registrar", "modificar", "desactivar"):
            RoleCrudPermission.objects.create(
                role=User.Role.BARBERO,
                app_key=RoleCrudPermission.AppKey.COMPRAS,
                action=action,
            )
        self.client.login(username="barbero", password="pass1234")
        response = self.client.get(self._url("compras"))
        self.assertTrue(response.context["can_register_compras"])
        self.assertTrue(response.context["can_modify_compras"])
        self.assertTrue(response.context["can_deactivate_compras"])

    def test_context_admin_always_true(self):
        self.client.login(username="admin", password="pass1234")
        response = self.client.get(self._url("compras"))
        self.assertTrue(response.context["can_register_compras"])
        self.assertTrue(response.context["can_modify_compras"])
        self.assertTrue(response.context["can_deactivate_compras"])

    # ── POST: create (save) ──

    def test_create_purchase_without_permission(self):
        self.client.login(username="barbero", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "compras",
                "action": "save",
                "product": str(self.product.pk),
                "quantity": "5",
                "unit_cost": "6000",
            },
        )
        self.assertRedirects(response, f"{self.list_url}?section=compras&view=list")

    def test_create_purchase_with_permission(self):
        RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key=RoleCrudPermission.AppKey.COMPRAS,
            action="registrar",
        )
        self.client.login(username="barbero", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "compras",
                "action": "save",
                "product": str(self.product.pk),
                "quantity": "5",
                "unit_cost": "6000",
            },
        )
        self.assertRedirects(response, f"{self.list_url}?section=compras&view=list")

    # ── POST: update ──

    def test_update_purchase_without_permission(self):
        self.client.login(username="barbero", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "compras",
                "action": "update",
                "purchase_id": str(self.purchase.pk),
                "quantity": "20",
                "unit_cost": "4000",
            },
        )
        self.assertRedirects(response, self._url("compras"))
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.quantity, 10)

    def test_update_purchase_with_permission(self):
        RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key=RoleCrudPermission.AppKey.COMPRAS,
            action="modificar",
        )
        self.client.login(username="barbero", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "compras",
                "action": "update",
                "purchase_id": str(self.purchase.pk),
                "quantity": "20",
                "unit_cost": "4000",
            },
        )
        self.assertRedirects(response, self._url("compras"))
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.quantity, 20)

    # ── POST: deactivate (anular) ──

    def test_deactivate_purchase_without_permission(self):
        self.client.login(username="barbero", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "compras",
                "action": "deactivate",
                "purchase_id": str(self.purchase.pk),
            },
        )
        self.assertRedirects(response, self._url("compras"))
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.status, Purchase.Status.ACTIVE)

    def test_deactivate_purchase_with_permission(self):
        RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key=RoleCrudPermission.AppKey.COMPRAS,
            action="desactivar",
        )
        self.client.login(username="barbero", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "compras",
                "action": "deactivate",
                "purchase_id": str(self.purchase.pk),
            },
        )
        self.assertRedirects(response, self._url("compras"))
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.status, Purchase.Status.CANCELED)

    # ── GET form (registrar) ──

    def test_get_form_without_register_permission(self):
        self.client.login(username="barbero", password="pass1234")
        response = self.client.get(self._url("compras", view="form"))
        self.assertRedirects(response, self._url("compras"))

    def test_get_form_with_register_permission(self):
        RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key=RoleCrudPermission.AppKey.COMPRAS,
            action="registrar",
        )
        self.client.login(username="barbero", password="pass1234")
        response = self.client.get(self._url("compras", view="form"))
        self.assertEqual(response.status_code, 200)

    # ── GET edit (modificar) ──

    def test_get_edit_without_modify_permission(self):
        self.client.login(username="barbero", password="pass1234")
        response = self.client.get(
            self._url("compras", view="edit", purchase=self.purchase.pk)
        )
        self.assertRedirects(response, self._url("compras"))

    def test_get_edit_with_modify_permission(self):
        RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key=RoleCrudPermission.AppKey.COMPRAS,
            action="modificar",
        )
        self.client.login(username="barbero", password="pass1234")
        response = self.client.get(
            self._url("compras", view="edit", purchase=self.purchase.pk)
        )
        self.assertEqual(response.status_code, 200)

    # ── Admin bypass ──

    def test_admin_bypasses_crud_checks(self):
        self.client.login(username="admin", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "compras",
                "action": "deactivate",
                "purchase_id": str(self.purchase.pk),
            },
        )
        self.assertRedirects(response, self._url("compras"))
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.status, Purchase.Status.CANCELED)

    def test_admin_register_form_always_accessible(self):
        self.client.login(username="admin", password="pass1234")
        response = self.client.get(self._url("compras", view="form"))
        self.assertEqual(response.status_code, 200)

    def test_admin_edit_always_accessible(self):
        self.client.login(username="admin", password="pass1234")
        response = self.client.get(
            self._url("compras", view="edit", purchase=self.purchase.pk)
        )
        self.assertEqual(response.status_code, 200)

    # ── Estilista blocked (no crud permissions created) ──

    def test_estilista_blocked_all_crud_actions(self):
        self.client.login(username="estilista", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "compras",
                "action": "deactivate",
                "purchase_id": str(self.purchase.pk),
            },
        )
        self.assertRedirects(response, self._url("compras"))
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.status, Purchase.Status.ACTIVE)

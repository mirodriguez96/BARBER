from django.test import TestCase
from django.urls import reverse

from barberia.accounts.models import User
from barberia.catalog.models import CatalogItem
from barberia.dashboard.models import RoleCrudPermission, RoleMenuPermission


class CrudProductosPermissionTest(TestCase):
    """CRUD permission enforcement for app_key='productos' (catalog section)."""

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

        self.catalog_item = CatalogItem.objects.create(
            name="Test Service",
            kind="service",
            price=50000,
        )

        RoleMenuPermission.objects.create(role=User.Role.BARBERO, menu_key="catalog")
        RoleMenuPermission.objects.create(role=User.Role.ESTILISTA, menu_key="catalog")

    def _url(self, section, view="list", **kwargs):
        url = f"{self.list_url}?section={section}&view={view}"
        for k, v in kwargs.items():
            url += f"&{k}={v}"
        return url

    # ── Context ──

    def test_context_without_permissions(self):
        self.client.login(username="barbero", password="pass1234")
        response = self.client.get(self._url("catalog"))
        self.assertFalse(response.context["can_register_productos"])
        self.assertFalse(response.context["can_modify_productos"])
        self.assertFalse(response.context["can_deactivate_productos"])

    def test_context_with_all_permissions(self):
        for action in ("registrar", "modificar", "desactivar"):
            RoleCrudPermission.objects.create(
                role=User.Role.BARBERO,
                app_key=RoleCrudPermission.AppKey.PRODUCTOS,
                action=action,
            )
        self.client.login(username="barbero", password="pass1234")
        response = self.client.get(self._url("catalog"))
        self.assertTrue(response.context["can_register_productos"])
        self.assertTrue(response.context["can_modify_productos"])
        self.assertTrue(response.context["can_deactivate_productos"])

    def test_context_admin_always_true(self):
        self.client.login(username="admin", password="pass1234")
        response = self.client.get(self._url("catalog"))
        self.assertTrue(response.context["can_register_productos"])
        self.assertTrue(response.context["can_modify_productos"])
        self.assertTrue(response.context["can_deactivate_productos"])

    # ── POST: deactivate ──

    def test_deactivate_catalog_item_without_permission(self):
        self.client.login(username="barbero", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "catalog",
                "action": "deactivate",
                "catalog_item_id": self.catalog_item.pk,
            },
        )
        self.assertRedirects(response, self._url("catalog"))
        self.catalog_item.refresh_from_db()
        self.assertTrue(self.catalog_item.is_active)

    def test_deactivate_catalog_item_with_permission(self):
        RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key=RoleCrudPermission.AppKey.PRODUCTOS,
            action="desactivar",
        )
        self.client.login(username="barbero", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "catalog",
                "action": "deactivate",
                "catalog_item_id": self.catalog_item.pk,
            },
        )
        self.assertRedirects(response, self._url("catalog"))
        self.catalog_item.refresh_from_db()
        self.assertFalse(self.catalog_item.is_active)

    # ── POST: activate ──

    def test_activate_catalog_item_without_permission(self):
        self.catalog_item.is_active = False
        self.catalog_item.save()
        self.client.login(username="barbero", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "catalog",
                "action": "activate",
                "catalog_item_id": self.catalog_item.pk,
            },
        )
        self.assertRedirects(response, self._url("catalog"))
        self.catalog_item.refresh_from_db()
        self.assertFalse(self.catalog_item.is_active)

    def test_activate_catalog_item_with_permission(self):
        self.catalog_item.is_active = False
        self.catalog_item.save()
        RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key=RoleCrudPermission.AppKey.PRODUCTOS,
            action="desactivar",
        )
        self.client.login(username="barbero", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "catalog",
                "action": "activate",
                "catalog_item_id": self.catalog_item.pk,
            },
        )
        self.assertRedirects(response, self._url("catalog"))
        self.catalog_item.refresh_from_db()
        self.assertTrue(self.catalog_item.is_active)

    # ── POST: update ──

    def test_update_catalog_item_without_permission(self):
        self.client.login(username="barbero", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "catalog",
                "action": "update",
                "catalog_item_id": self.catalog_item.pk,
                "name": "Hacked Name",
                "kind": "service",
                "price": "99999",
            },
        )
        self.assertRedirects(response, self._url("catalog"))
        self.catalog_item.refresh_from_db()
        self.assertEqual(self.catalog_item.name, "Test Service")

    def test_update_catalog_item_with_permission(self):
        RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key=RoleCrudPermission.AppKey.PRODUCTOS,
            action="modificar",
        )
        self.client.login(username="barbero", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "catalog",
                "action": "update",
                "catalog_item_id": self.catalog_item.pk,
                "name": "Updated Service",
                "kind": "service",
                "price": "60000",
                "barber_commission_percent": "20.00",
            },
        )
        self.assertRedirects(response, self._url("catalog"))
        self.catalog_item.refresh_from_db()
        self.assertEqual(self.catalog_item.name, "Updated Service")

    # ── GET form (registrar) ──

    def test_get_form_without_register_permission(self):
        self.client.login(username="barbero", password="pass1234")
        response = self.client.get(self._url("catalog", view="form"))
        self.assertRedirects(response, self._url("catalog"))

    def test_get_form_with_register_permission(self):
        RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key=RoleCrudPermission.AppKey.PRODUCTOS,
            action="registrar",
        )
        self.client.login(username="barbero", password="pass1234")
        response = self.client.get(self._url("catalog", view="form"))
        self.assertEqual(response.status_code, 200)

    # ── GET edit (modificar) ──

    def test_get_edit_without_modify_permission(self):
        self.client.login(username="barbero", password="pass1234")
        response = self.client.get(
            self._url("catalog", view="edit", catalog_item=self.catalog_item.pk)
        )
        self.assertRedirects(response, self._url("catalog"))

    def test_get_edit_with_modify_permission(self):
        RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key=RoleCrudPermission.AppKey.PRODUCTOS,
            action="modificar",
        )
        self.client.login(username="barbero", password="pass1234")
        response = self.client.get(
            self._url("catalog", view="edit", catalog_item=self.catalog_item.pk)
        )
        self.assertEqual(response.status_code, 200)

    # ── Admin bypass ──

    def test_admin_bypasses_crud_checks(self):
        self.client.login(username="admin", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "catalog",
                "action": "deactivate",
                "catalog_item_id": self.catalog_item.pk,
            },
        )
        self.assertRedirects(response, self._url("catalog"))
        self.catalog_item.refresh_from_db()
        self.assertFalse(self.catalog_item.is_active)

    def test_admin_register_form_always_accessible(self):
        self.client.login(username="admin", password="pass1234")
        response = self.client.get(self._url("catalog", view="form"))
        self.assertEqual(response.status_code, 200)

    def test_admin_edit_always_accessible(self):
        self.client.login(username="admin", password="pass1234")
        response = self.client.get(
            self._url("catalog", view="edit", catalog_item=self.catalog_item.pk)
        )
        self.assertEqual(response.status_code, 200)

    # ── Estilista blocked (no crud permissions created) ──

    def test_estilista_blocked_all_crud_actions(self):
        self.client.login(username="estilista", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "catalog",
                "action": "deactivate",
                "catalog_item_id": self.catalog_item.pk,
            },
        )
        self.assertRedirects(response, self._url("catalog"))
        self.catalog_item.refresh_from_db()
        self.assertTrue(self.catalog_item.is_active)  # unchanged

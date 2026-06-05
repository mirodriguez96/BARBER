from datetime import datetime

from django.test import TestCase
from django.urls import reverse

from barberia.accounts.models import User
from barberia.catalog.models import CatalogItem
from barberia.dashboard.models import RoleCrudPermission, RoleMenuPermission
from barberia.operations.models import Sale
from barberia.people.models import Employee


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
        """Verifica que un usuario sin permisos CRUD vea todas las flags de permiso como False en el contexto."""
        self.client.login(username="barbero", password="pass1234")
        response = self.client.get(self._url("sales"))
        self.assertFalse(response.context["can_register_ventas"])
        self.assertFalse(response.context["can_modify_ventas"])
        self.assertFalse(response.context["can_deactivate_ventas"])

    def test_context_with_all_permissions(self):
        """Verifica que un usuario con los tres permisos CRUD vea todas las flags como True en el contexto."""
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
        """Verifica que un administrador vea siempre todas las flags de permiso como True, sin necesidad de permisos explícitos."""
        self.client.login(username="admin", password="pass1234")
        response = self.client.get(self._url("sales"))
        self.assertTrue(response.context["can_register_ventas"])
        self.assertTrue(response.context["can_modify_ventas"])
        self.assertTrue(response.context["can_deactivate_ventas"])

    # ── POST: create ──

    def test_create_sale_without_permission(self):
        """Verifica que un usuario sin permiso 'registrar' sea redirigido al intentar crear una venta."""
        self.client.login(username="barbero", password="pass1234")
        response = self.client.post(
            self.list_url,
            {
                "section": "sales",
            },
        )
        self.assertRedirects(response, self._url("sales"))

    def test_create_sale_with_permission(self):
        """Verifica que un usuario con permiso 'registrar' pueda crear una venta exitosamente."""
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
        """Verifica que un usuario sin permiso 'modificar' sea redirigido y la venta no sea alterada."""
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
        """Verifica que un usuario con permiso 'modificar' pueda actualizar una venta exitosamente."""
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
        """Verifica que un usuario sin permiso 'desactivar' sea redirigido y la venta mantenga su estado original."""
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
        """Verifica que un usuario con permiso 'desactivar' pueda cancelar una venta exitosamente."""
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
        """Verifica que un usuario sin permiso 'registrar' sea redirigido al intentar acceder al formulario de registro."""
        self.client.login(username="barbero", password="pass1234")
        response = self.client.get(self._url("sales", view="form"))
        self.assertRedirects(response, self._url("sales"))

    def test_get_form_with_register_permission(self):
        """Verifica que un usuario con permiso 'registrar' pueda acceder al formulario de registro."""
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
        """Verifica que un usuario sin permiso 'modificar' sea redirigido al intentar acceder al formulario de edición."""
        self.client.login(username="barbero", password="pass1234")
        response = self.client.get(self._url("sales", view="edit", sale=self.sale.pk))
        self.assertRedirects(response, self._url("sales"))

    def test_get_edit_with_modify_permission(self):
        """Verifica que un usuario con permiso 'modificar' pueda acceder al formulario de edición."""
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
        """Verifica que un administrador pueda ejecutar cualquier acción CRUD sin necesidad de permisos explícitos."""
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
        """Verifica que un estilista sin permisos CRUD sea redirigido y no pueda modificar ninguna venta."""
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

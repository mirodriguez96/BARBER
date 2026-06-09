from datetime import datetime
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from barberia.accounts.models import User
from barberia.catalog.models import CatalogItem
from barberia.common.tests.pagination_mixin import PaginationTestMixin
from barberia.dashboard.models import RoleCrudPermission, RoleMenuPermission
from barberia.inventory.models import InventoryMovement
from barberia.operations.models import Purchase, Sale
from barberia.people.models import Client, Employee
from barberia.routers import set_current_db_name


class SalesFullLifecycleTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        set_current_db_name(None)

    def setUp(self):
        set_current_db_name(None)
        self.user = User.objects.create_user(
            username="admin",
            password="pass1234",
            role=User.Role.ADMIN,
        )
        self.client.login(username="admin", password="pass1234")
        self.url = reverse("dashboard:home")
        self.employee = Employee.objects.create(
            user=self.user,
            full_name="Barber Test",
            document_id="DOC-SALES",
            phone="700000001",
        )
        self.client_model = Client.objects.create(
            full_name="Client Test",
            phone="700000002",
        )
        self.service = CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Corte Clásico",
            price=Decimal("50.00"),
            barber_commission_percent=Decimal("20.00"),
            is_active=True,
        )
        self.product = CatalogItem.objects.create(
            kind=CatalogItem.Kind.PRODUCT,
            name="Gel Fijador",
            price=Decimal("30.00"),
            current_stock=20,
            is_active=True,
        )

    def tearDown(self):
        set_current_db_name(None)

    def _sales_list_url(self):
        return f"{self.url}?section=sales&view=list"

    def _sales_section_url(self):
        return f"{self.url}?section=sales"

    def _now_str(self):
        return timezone.localtime().strftime("%Y-%m-%dT%H:%M")

    # --- Service sale: full lifecycle create -> edit -> cancel ---

    def test_service_sale_full_lifecycle(self):
        create_data = {
            "section": "sales",
            "employee": self.employee.pk,
            "client": self.client_model.pk,
            "product": self.service.pk,
            "scheduled_for": self._now_str(),
            "product_price": "50.00",
            "commission_amount": "20.00",
            "tip_amount": "5.00",
            "notes": "Servicio completo",
        }
        response = self.client.post(self.url, create_data)
        self.assertRedirects(response, self._sales_section_url())
        sale = Sale.objects.get(notes="Servicio completo")
        self.assertEqual(sale.status, Sale.Status.DONE)
        self.assertEqual(sale.product_price, Decimal("50.00"))
        self.assertEqual(sale.commission_amount, Decimal("20.00"))
        self.assertEqual(sale.tip_amount, Decimal("5.00"))

        edit_data = {
            "section": "sales",
            "action": "update",
            "sale_id": str(sale.pk),
            "employee": self.employee.pk,
            "product": self.service.pk,
            "product_price": "60.00",
            "commission_amount": "12.00",
            "tip_amount": "8.00",
            "notes": "Servicio actualizado",
        }
        response = self.client.post(self.url, edit_data)
        self.assertRedirects(response, self._sales_list_url())
        sale.refresh_from_db()
        self.assertEqual(sale.product_price, Decimal("50.00"))
        self.assertEqual(sale.commission_amount, Decimal("20.00"))
        self.assertEqual(sale.tip_amount, Decimal("8.00"))
        self.assertEqual(sale.notes, "Servicio actualizado")

        cancel_data = {
            "section": "sales",
            "action": "cancel",
            "sale_id": str(sale.pk),
        }
        response = self.client.post(self.url, cancel_data)
        self.assertRedirects(response, self._sales_list_url())
        sale.refresh_from_db()
        self.assertEqual(sale.status, Sale.Status.CANCELED)

    # --- Product sale: creates inventory movement ---

    def test_product_sale_decrements_stock(self):
        pre_stock = CatalogItem.objects.get(pk=self.product.pk).current_stock
        create_data = {
            "section": "sales",
            "type": "producto",
            "product": self.product.pk,
            "quantity": "3",
            "product_price": "30.00",
            "notes": "Venta de productos",
        }
        response = self.client.post(self.url, create_data)
        self.assertRedirects(response, self._sales_section_url())
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, pre_stock - 3)
        self.assertTrue(Sale.objects.filter(notes="Venta de productos").exists())
        self.assertTrue(
            InventoryMovement.objects.filter(
                product=self.product,
                movement_type=InventoryMovement.MovementType.SALE,
                quantity=-3,
            ).exists()
        )

    def test_product_sale_cancel_reverts_stock(self):
        pre_stock = CatalogItem.objects.get(pk=self.product.pk).current_stock
        create_data = {
            "section": "sales",
            "type": "producto",
            "product": self.product.pk,
            "quantity": "5",
            "product_price": "30.00",
            "notes": "Venta a cancelar",
        }
        response = self.client.post(self.url, create_data)
        self.assertRedirects(response, self._sales_section_url())
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, pre_stock - 5)
        sale = Sale.objects.get(notes="Venta a cancelar")

        cancel_data = {
            "section": "sales",
            "action": "cancel",
            "sale_id": str(sale.pk),
        }
        response = self.client.post(self.url, cancel_data)
        self.assertRedirects(response, self._sales_list_url())
        sale.refresh_from_db()
        self.assertEqual(sale.status, Sale.Status.CANCELED)
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, pre_stock)

    def test_product_sale_edit_quantity_adjusts_stock(self):
        initial_stock = 20

        create_data = {
            "section": "sales",
            "type": "producto",
            "product": self.product.pk,
            "quantity": "3",
            "product_price": "30.00",
            "notes": "Venta a editar",
        }
        response = self.client.post(self.url, create_data)
        self.assertRedirects(response, self._sales_section_url())
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, initial_stock - 3)
        sale = Sale.objects.get(notes="Venta a editar")

        edit_data = {
            "section": "sales",
            "action": "update",
            "sale_id": str(sale.pk),
            "product": self.product.pk,
            "quantity": "7",
            "product_price": "30.00",
        }
        response = self.client.post(self.url, edit_data)
        self.assertRedirects(response, self._sales_list_url())
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, initial_stock - 7)

    # --- Validation: service sale requires employee ---

    def test_service_sale_without_employee_rejected(self):
        data = {
            "section": "sales",
            "client": self.client_model.pk,
            "product": self.service.pk,
            "scheduled_for": self._now_str(),
            "product_price": "50.00",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)

    # --- Permission-based access ---

    def test_barbero_sees_own_sales_only(self):
        another_user = User.objects.create_user(
            username="another_barber",
            password="pass1234",
            role=User.Role.BARBERO,
        )
        another_employee = Employee.objects.create(
            user=another_user,
            full_name="Another Barber",
            document_id="DOC-ANOTHER",
            phone="700000003",
        )
        Sale.objects.create(
            employee=self.employee,
            product=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
        )
        Sale.objects.create(
            employee=another_employee,
            product=self.service,
            performed_by=another_user,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
        )
        self.client.logout()
        barbero = User.objects.create_user(
            username="sales_barber",
            password="pass1234",
            role=User.Role.BARBERO,
        )
        barber_employee = Employee.objects.create(
            user=barbero,
            full_name="Sales Barber",
            document_id="DOC-SALES-BARBER",
            phone="700000004",
        )
        RoleMenuPermission.objects.create(role=User.Role.BARBERO, menu_key="sales")
        RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key=RoleCrudPermission.AppKey.VENTAS,
            action=RoleCrudPermission.Action.REGISTRAR,
        )
        Sale.objects.create(
            employee=barber_employee,
            product=self.service,
            performed_by=barbero,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
        )
        self.client.login(username="sales_barber", password="pass1234")
        response = self.client.get(self._sales_list_url())
        self.assertEqual(response.status_code, 200)
        sales = list(response.context["sales"].object_list)
        for s in sales:
            self.assertEqual(s.employee.pk, barber_employee.pk)

    def test_non_admin_blocked_from_sales_without_menu_permission(self):
        self.client.logout()
        _ = User.objects.create_user(
            username="no_sales_view",
            password="pass1234",
            role=User.Role.BARBERO,
        )
        RoleMenuPermission.objects.create(role=User.Role.BARBERO, menu_key="overview")
        self.client.login(username="no_sales_view", password="pass1234")
        response = self.client.get(f"{self.url}?section=sales")
        self.assertRedirects(response, f"{self.url}?section=overview")

    def test_non_admin_cannot_create_sale_without_crud_permission(self):
        self.client.logout()
        _ = User.objects.create_user(
            username="no_create_sale",
            password="pass1234",
            role=User.Role.BARBERO,
        )
        RoleMenuPermission.objects.create(role=User.Role.BARBERO, menu_key="sales")
        self.client.login(username="no_create_sale", password="pass1234")
        data = {
            "section": "sales",
            "employee": self.employee.pk,
            "product": self.service.pk,
            "scheduled_for": self._now_str(),
            "product_price": "50.00",
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, self._sales_list_url())


class PurchasesFullLifecycleTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        set_current_db_name(None)

    def setUp(self):
        set_current_db_name(None)
        self.user = User.objects.create_user(
            username="admin",
            password="pass1234",
            role=User.Role.ADMIN,
        )
        self.client.login(username="admin", password="pass1234")
        self.url = reverse("dashboard:home")
        self.product = CatalogItem.objects.create(
            kind=CatalogItem.Kind.PRODUCT,
            name="Producto Compra",
            price=Decimal("25.00"),
            current_stock=10,
            is_active=True,
        )

    def tearDown(self):
        set_current_db_name(None)

    def _compras_list_url(self):
        return f"{self.url}?section=compras&view=list"

    # --- Purchase full lifecycle: create -> edit -> cancel ---

    def test_purchase_full_lifecycle(self):
        pre_stock = CatalogItem.objects.get(pk=self.product.pk).current_stock

        create_data = {
            "section": "compras",
            "action": "save",
            "product": self.product.pk,
            "quantity": "15",
            "unit_cost": "20.00",
            "notes": "Compra de prueba",
        }
        response = self.client.post(self.url, create_data)
        self.assertRedirects(response, self._compras_list_url())
        purchase = Purchase.objects.get(notes="Compra de prueba")
        self.assertEqual(purchase.quantity, 15)
        self.assertEqual(purchase.unit_cost, Decimal("20.00"))
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, pre_stock + 15)

        edit_data = {
            "section": "compras",
            "action": "update",
            "purchase_id": str(purchase.pk),
            "quantity": "20",
            "unit_cost": "18.00",
            "notes": "Compra actualizada",
        }
        response = self.client.post(self.url, edit_data)
        self.assertRedirects(response, self._compras_list_url())
        purchase.refresh_from_db()
        self.assertEqual(purchase.quantity, 20)
        self.assertEqual(purchase.unit_cost, Decimal("18.00"))
        self.assertEqual(purchase.notes, "Compra actualizada")
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, pre_stock + 20)

        cancel_data = {
            "section": "compras",
            "action": "deactivate",
            "purchase_id": str(purchase.pk),
        }
        response = self.client.post(self.url, cancel_data)
        self.assertRedirects(response, self._compras_list_url())
        purchase.refresh_from_db()
        self.assertEqual(purchase.status, Purchase.Status.CANCELED)
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, pre_stock)

    # --- Invalid purchase ---

    def test_purchase_without_product_rejected(self):
        data = {
            "section": "compras",
            "action": "save",
            "product": "",
            "quantity": "5",
            "unit_cost": "10.00",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("purchase_form", response.context)

    def test_purchase_with_negative_quantity_rejected(self):
        data = {
            "section": "compras",
            "action": "save",
            "product": self.product.pk,
            "quantity": "-5",
            "unit_cost": "10.00",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("purchase_form", response.context)

    # --- Permission-based access ---

    def test_non_admin_blocked_from_purchases_without_menu_permission(self):
        self.client.logout()
        _ = User.objects.create_user(
            username="no_compras",
            password="pass1234",
            role=User.Role.BARBERO,
        )
        RoleMenuPermission.objects.create(role=User.Role.BARBERO, menu_key="overview")
        self.client.login(username="no_compras", password="pass1234")
        response = self.client.get(f"{self.url}?section=compras")
        self.assertRedirects(response, f"{self.url}?section=overview")

    def test_non_admin_cannot_create_purchase_without_crud_permission(self):
        self.client.logout()
        _ = User.objects.create_user(
            username="no_compra_crud",
            password="pass1234",
            role=User.Role.BARBERO,
        )
        RoleMenuPermission.objects.create(role=User.Role.BARBERO, menu_key="compras")
        self.client.login(username="no_compra_crud", password="pass1234")
        data = {
            "section": "compras",
            "action": "save",
            "product": self.product.pk,
            "quantity": "5",
            "unit_cost": "10.00",
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, f"{self.url}?section=compras&view=list")

    def test_non_admin_can_create_purchase_with_crud_permission(self):
        self.client.logout()
        _ = User.objects.create_user(
            username="compra_crud",
            password="pass1234",
            role=User.Role.BARBERO,
        )
        RoleMenuPermission.objects.create(role=User.Role.BARBERO, menu_key="compras")
        RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key=RoleCrudPermission.AppKey.COMPRAS,
            action=RoleCrudPermission.Action.REGISTRAR,
        )
        self.client.login(username="compra_crud", password="pass1234")
        data = {
            "section": "compras",
            "action": "save",
            "product": self.product.pk,
            "quantity": "3",
            "unit_cost": "12.00",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Purchase.objects.filter(quantity=3).exists())

    def test_cancel_already_canceled_purchase_does_not_duplicate_movement(self):
        purchase = Purchase.objects.create(
            product=self.product,
            quantity=10,
            unit_cost=Decimal("15.00"),
            created_by=self.user,
            status=Purchase.Status.CANCELED,
        )
        pre_stock = CatalogItem.objects.get(pk=self.product.pk).current_stock

        data = {
            "section": "compras",
            "action": "deactivate",
            "purchase_id": str(purchase.pk),
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, self._compras_list_url())
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, pre_stock)


class InventoryAdjustmentTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        set_current_db_name(None)

    def setUp(self):
        set_current_db_name(None)
        self.user = User.objects.create_user(
            username="admin",
            password="pass1234",
            role=User.Role.ADMIN,
        )
        self.client.login(username="admin", password="pass1234")
        self.url = reverse("dashboard:home")
        self.product = CatalogItem.objects.create(
            kind=CatalogItem.Kind.PRODUCT,
            name="Producto Ajustable",
            price=Decimal("40.00"),
            current_stock=50,
            is_active=True,
        )

    def tearDown(self):
        set_current_db_name(None)

    def test_inventory_adjustment_increase_stock(self):
        pre_stock = CatalogItem.objects.get(pk=self.product.pk).current_stock
        data = {
            "section": "inventory",
            "action": "adjust",
            "product": self.product.pk,
            "quantity": "10",
            "is_supply": False,
            "notes": "Ajuste aumento",
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, f"{self.url}?section=inventory&view=list")
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, pre_stock + 10)
        self.assertTrue(
            InventoryMovement.objects.filter(
                product=self.product,
                movement_type=InventoryMovement.MovementType.ADJUSTMENT,
                quantity=10,
            ).exists()
        )

    def test_inventory_adjustment_decrease_stock(self):
        pre_stock = CatalogItem.objects.get(pk=self.product.pk).current_stock
        data = {
            "section": "inventory",
            "action": "adjust",
            "product": self.product.pk,
            "quantity": "-15",
            "is_supply": False,
            "notes": "Ajuste disminución",
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, f"{self.url}?section=inventory&view=list")
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, pre_stock - 15)

    def test_inventory_adjustment_supply_negates_quantity(self):
        pre_stock = CatalogItem.objects.get(pk=self.product.pk).current_stock
        data = {
            "section": "inventory",
            "action": "adjust",
            "product": self.product.pk,
            "quantity": "5",
            "is_supply": True,
            "notes": "Uso de insumo",
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, f"{self.url}?section=inventory&view=list")
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, pre_stock - 5)
        movement = InventoryMovement.objects.get(
            product=self.product, notes="Uso de insumo"
        )
        self.assertEqual(movement.quantity, -5)
        self.assertTrue(movement.is_supply)

    def test_inventory_adjustment_without_product_rejected(self):
        data = {
            "section": "inventory",
            "action": "adjust",
            "product": "",
            "quantity": "5",
            "is_supply": False,
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("inventory_adjust_form", response.context)

    def test_non_admin_blocked_from_inventory_adjustment(self):
        self.client.logout()
        _ = User.objects.create_user(
            username="no_inv_adj",
            password="pass1234",
            role=User.Role.BARBERO,
        )
        RoleMenuPermission.objects.create(role=User.Role.BARBERO, menu_key="inventory")
        self.client.login(username="no_inv_adj", password="pass1234")
        data = {
            "section": "inventory",
            "action": "adjust",
            "product": self.product.pk,
            "quantity": "5",
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, f"{self.url}?section=inventory&view=list")

    def test_non_admin_can_adjust_with_crud_permission(self):
        self.client.logout()
        _ = User.objects.create_user(
            username="inv_adj_crud",
            password="pass1234",
            role=User.Role.BARBERO,
        )
        RoleMenuPermission.objects.create(role=User.Role.BARBERO, menu_key="inventory")
        RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key=RoleCrudPermission.AppKey.INVENTARIO,
            action=RoleCrudPermission.Action.AJUSTAR,
        )
        self.client.login(username="inv_adj_crud", password="pass1234")
        data = {
            "section": "inventory",
            "action": "adjust",
            "product": self.product.pk,
            "quantity": "8",
            "is_supply": False,
            "notes": "Ajuste permitido",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, 58)


class SalesPaginationIntegrationTest(PaginationTestMixin, TestCase):
    section_name = "sales"
    context_key = "sales"

    def setUp(self):
        set_current_db_name(None)
        self.user = User.objects.create_user(
            username="admin",
            password="pass1234",
            role=User.Role.ADMIN,
        )
        self.employee_user = User.objects.create_user(
            username="barbero1",
            password="pass1234",
            role=User.Role.BARBERO,
        )
        self.employee = Employee.objects.create(
            user=self.employee_user,
            full_name="Colaborador Uno",
            document_id="DOC001",
            phone="70000001",
        )
        self.client_model = Client.objects.create(full_name="Cliente Test")
        self.service = CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Corte",
            price=Decimal("50.00"),
            barber_commission_percent=Decimal("20.00"),
        )
        self.client.login(username="admin", password="pass1234")
        self.url = reverse("dashboard:home")

    def tearDown(self):
        set_current_db_name(None)

    def _create_pagination_items(self, count: int):
        for i in range(count):
            Sale.objects.create(
                employee=self.employee,
                client=self.client_model if i % 2 == 0 else None,
                product=self.service,
                performed_by=self.user,
                scheduled_for=timezone.make_aware(datetime(2025, 1, 1, i, 0, 0)),
                product_price=Decimal("50.00"),
                commission_amount=Decimal("10.00"),
            )

    def test_filter_plus_pagination(self):
        self._create_pagination_items(15)
        page = self._get_pagination_page(page="2", filter_barber=self.employee.pk)
        self.assertEqual(len(list(page.object_list)), 5)


class SalesFilterTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        set_current_db_name(None)

    def setUp(self):
        set_current_db_name(None)
        self.user = User.objects.create_user(
            username="admin",
            password="pass1234",
            role=User.Role.ADMIN,
        )
        self.employee1 = Employee.objects.create(
            full_name="Filter Barber 1",
            document_id="FIL-B1",
            phone="730000001",
        )
        self.employee2 = Employee.objects.create(
            full_name="Filter Barber 2",
            document_id="FIL-B2",
            phone="730000002",
        )
        self.service = CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Filter Service",
            price=Decimal("50.00"),
        )
        self.product = CatalogItem.objects.create(
            kind=CatalogItem.Kind.PRODUCT,
            name="Filter Product",
            price=Decimal("30.00"),
        )
        self.client.login(username="admin", password="pass1234")
        self.url = reverse("dashboard:home")
        Sale.objects.create(
            employee=self.employee1,
            product=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
        )
        Sale.objects.create(
            employee=self.employee2,
            product=self.product,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("30.00"),
            quantity=2,
        )

    def tearDown(self):
        set_current_db_name(None)

    def test_filter_by_barber(self):
        response = self.client.get(
            f"{self.url}?section=sales&filter_barber={self.employee1.pk}"
        )
        self.assertEqual(response.status_code, 200)
        sales = list(response.context["sales"].object_list)
        for s in sales:
            self.assertEqual(s.employee_id, self.employee1.pk)

    def test_filter_by_kind_service(self):
        response = self.client.get(f"{self.url}?section=sales&filter_kind=service")
        self.assertEqual(response.status_code, 200)
        sales = list(response.context["sales"].object_list)
        for s in sales:
            self.assertEqual(s.product.kind, CatalogItem.Kind.SERVICE)

    def test_filter_by_kind_product(self):
        response = self.client.get(f"{self.url}?section=sales&filter_kind=product")
        self.assertEqual(response.status_code, 200)
        sales = list(response.context["sales"].object_list)
        for s in sales:
            self.assertEqual(s.product.kind, CatalogItem.Kind.PRODUCT)

    def test_filter_by_date_today(self):
        response = self.client.get(f"{self.url}?section=sales&filter_date=today")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(list(response.context["sales"].object_list)), 2)

    def test_sale_stats(self):
        response = self.client.get(f"{self.url}?section=sales")
        self.assertEqual(response.status_code, 200)
        stats = response.context["sale_stats"]
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["sales"], 1)
        self.assertEqual(stats["products"], 1)


class SaleStatusTransitionTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        set_current_db_name(None)

    def setUp(self):
        set_current_db_name(None)
        self.user = User.objects.create_user(
            username="admin_transitions",
            password="pass1234",
            role=User.Role.ADMIN,
        )
        self.employee = Employee.objects.create(
            full_name="Transitions Barber",
            document_id="DOC-TRANS",
            phone="740000001",
        )
        self.service = CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Transition Service",
            price=Decimal("60.00"),
        )
        self.client.login(username="admin_transitions", password="pass1234")
        self.url = reverse("dashboard:home")

    def tearDown(self):
        set_current_db_name(None)

    def _create_sale(self, **kwargs):
        data = {
            "section": "sales",
            "employee": self.employee.pk,
            "product": self.service.pk,
            "scheduled_for": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
            "product_price": "60.00",
            **kwargs,
        }
        return self.client.post(self.url, data)

    def _sales_list_url(self):
        return f"{self.url}?section=sales&view=list"

    def test_create_sale_is_done(self):
        response = self._create_sale()
        self.assertRedirects(response, f"{self.url}?section=sales")
        sale = Sale.objects.latest("id")
        self.assertEqual(sale.status, Sale.Status.DONE)

    def test_update_to_scheduled(self):
        response = self._create_sale()
        sale = Sale.objects.latest("id")
        edit_data = {
            "section": "sales",
            "action": "update",
            "sale_id": str(sale.pk),
            "employee": self.employee.pk,
            "product": self.service.pk,
            "status": Sale.Status.SCHEDULED,
        }
        response = self.client.post(self.url, edit_data)
        self.assertRedirects(response, self._sales_list_url())
        sale.refresh_from_db()
        self.assertEqual(sale.status, Sale.Status.SCHEDULED)

    def test_update_from_scheduled_to_done(self):
        response = self._create_sale()
        sale = Sale.objects.latest("id")
        self.client.post(
            self.url,
            {
                "section": "sales",
                "action": "update",
                "sale_id": str(sale.pk),
                "employee": self.employee.pk,
                "product": self.service.pk,
                "status": Sale.Status.SCHEDULED,
            },
        )
        sale.refresh_from_db()
        self.assertEqual(sale.status, Sale.Status.SCHEDULED)
        edit_data = {
            "section": "sales",
            "action": "update",
            "sale_id": str(sale.pk),
            "employee": self.employee.pk,
            "product": self.service.pk,
            "status": Sale.Status.DONE,
        }
        response = self.client.post(self.url, edit_data)
        self.assertRedirects(response, self._sales_list_url())
        sale.refresh_from_db()
        self.assertEqual(sale.status, Sale.Status.DONE)

    def test_cancel_done_sale(self):
        response = self._create_sale()
        sale = Sale.objects.latest("id")
        cancel_data = {
            "section": "sales",
            "action": "cancel",
            "sale_id": str(sale.pk),
        }
        response = self.client.post(self.url, cancel_data)
        self.assertRedirects(response, self._sales_list_url())
        sale.refresh_from_db()
        self.assertEqual(sale.status, Sale.Status.CANCELED)

    def test_cancel_scheduled_sale(self):
        self._create_sale()
        sale = Sale.objects.latest("id")
        self.client.post(
            self.url,
            {
                "section": "sales",
                "action": "update",
                "sale_id": str(sale.pk),
                "employee": self.employee.pk,
                "product": self.service.pk,
                "status": Sale.Status.SCHEDULED,
            },
        )
        sale.refresh_from_db()
        cancel_data = {
            "section": "sales",
            "action": "cancel",
            "sale_id": str(sale.pk),
        }
        self.client.post(self.url, cancel_data)
        sale.refresh_from_db()
        self.assertEqual(sale.status, Sale.Status.CANCELED)

    def test_cannot_edit_canceled_sale(self):
        response = self._create_sale()
        sale = Sale.objects.latest("id")
        self.client.post(
            self.url,
            {
                "section": "sales",
                "action": "cancel",
                "sale_id": str(sale.pk),
            },
        )
        sale.refresh_from_db()
        edit_data = {
            "section": "sales",
            "action": "update",
            "sale_id": str(sale.pk),
            "employee": self.employee.pk,
            "product": self.service.pk,
            "notes": "Should fail",
        }
        response = self.client.post(self.url, edit_data)
        self.assertRedirects(response, self._sales_list_url())
        sale.refresh_from_db()
        self.assertNotEqual(sale.notes, "Should fail")


class SaleProductChangeTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        set_current_db_name(None)

    def setUp(self):
        set_current_db_name(None)
        self.user = User.objects.create_user(
            username="admin_prod",
            password="pass1234",
            role=User.Role.ADMIN,
        )
        self.employee = Employee.objects.create(
            full_name="Prod Change Barber",
            document_id="DOC-PROD",
            phone="750000001",
        )
        self.product_a = CatalogItem.objects.create(
            kind=CatalogItem.Kind.PRODUCT,
            name="Producto A",
            price=Decimal("30.00"),
            current_stock=100,
        )
        self.product_b = CatalogItem.objects.create(
            kind=CatalogItem.Kind.PRODUCT,
            name="Producto B",
            price=Decimal("50.00"),
            current_stock=100,
        )
        self.client.login(username="admin_prod", password="pass1234")
        self.url = reverse("dashboard:home")

    def tearDown(self):
        set_current_db_name(None)

    def test_sale_change_product_a_to_b(self):
        response = self.client.post(
            self.url,
            {
                "section": "sales",
                "type": "producto",
                "product": self.product_a.pk,
                "quantity": "5",
                "product_price": "150.00",
            },
        )
        self.assertRedirects(response, f"{self.url}?section=sales")
        sale = Sale.objects.latest("id")
        self.product_a.refresh_from_db()
        self.assertEqual(self.product_a.current_stock, 95)
        edit_data = {
            "section": "sales",
            "action": "update",
            "sale_id": str(sale.pk),
            "product": self.product_b.pk,
            "quantity": "5",
            "product_price": "250.00",
            "employee": self.employee.pk,
        }
        response = self.client.post(self.url, edit_data)
        self.assertRedirects(response, f"{self.url}?section=sales&view=list")
        self.product_a.refresh_from_db()
        self.product_b.refresh_from_db()
        self.assertEqual(self.product_a.current_stock, 100)
        self.assertEqual(self.product_b.current_stock, 95)

    def test_sale_change_product_quantity(self):
        response = self.client.post(
            self.url,
            {
                "section": "sales",
                "type": "producto",
                "product": self.product_a.pk,
                "quantity": "5",
                "product_price": "150.00",
            },
        )
        self.assertRedirects(response, f"{self.url}?section=sales")
        sale = Sale.objects.latest("id")
        self.product_a.refresh_from_db()
        self.assertEqual(self.product_a.current_stock, 95)
        edit_data = {
            "section": "sales",
            "action": "update",
            "sale_id": str(sale.pk),
            "product": self.product_a.pk,
            "quantity": "8",
            "product_price": "240.00",
        }
        response = self.client.post(self.url, edit_data)
        self.assertRedirects(response, f"{self.url}?section=sales&view=list")
        self.product_a.refresh_from_db()
        self.assertEqual(self.product_a.current_stock, 92)


class SaleDateFilterTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        set_current_db_name(None)

    def setUp(self):
        set_current_db_name(None)
        self.user = User.objects.create_user(
            username="admin_filter",
            password="pass1234",
            role=User.Role.ADMIN,
        )
        self.service = CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Date Filter Service",
            price=Decimal("40.00"),
        )
        self.client.login(username="admin_filter", password="pass1234")
        self.url = reverse("dashboard:home")
        Sale.objects.create(
            product=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("40.00"),
        )

    def tearDown(self):
        set_current_db_name(None)

    def test_invalid_date_ignored(self):
        response = self.client.get(f"{self.url}?section=sales&filter_date=not-a-date")
        self.assertEqual(response.status_code, 200)
        sales = list(response.context["sales"].object_list)
        self.assertGreaterEqual(len(sales), 1)

    def test_future_date_shows_empty(self):
        response = self.client.get(f"{self.url}?section=sales&filter_date=2099-12-31")
        self.assertEqual(response.status_code, 200)
        sales = list(response.context["sales"].object_list)
        self.assertEqual(len(sales), 0)

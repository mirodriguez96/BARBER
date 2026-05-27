from decimal import Decimal
from urllib.parse import quote

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from barberia.accounts.models import User
from barberia.catalog.models import CatalogItem
from barberia.inventory.models import InventoryMovement
from barberia.operations.models import Sale
from barberia.people.models import Employee


class InventoryDashboardViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="admin_inv",
            password="pass1234",
            role=User.Role.ADMIN,
        )
        self.employee = Employee.objects.create(
            user=self.user,
            full_name="Admin Inventario",
            document_id="DOC200",
            phone="123456789",
        )
        self.product_1 = CatalogItem.objects.create(
            kind=CatalogItem.Kind.PRODUCT,
            name="Gel fijador",
            price=Decimal("100.00"),
            current_stock=20,
            sku="PRD100",
        )
        self.product_2 = CatalogItem.objects.create(
            kind=CatalogItem.Kind.PRODUCT,
            name="Shampoo",
            price=Decimal("150.00"),
            current_stock=0,
            sku="PRD150",
        )
        self.service_item = CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Corte degradado",
            price=Decimal("60.00"),
            barber_commission_percent=Decimal("20.00"),
            sku="SRV060",
        )
        self.client.login(username="admin_inv", password="pass1234")
        self.list_url = reverse("dashboard:home")

    def _inv_url(self, **params):
        params.setdefault("section", "inventory")
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.list_url}?{qs}"

    def _sales_url(self, **params):
        params.setdefault("section", "sales")
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.list_url}?{qs}"

    # --- Authentication ---

    def test_redirect_if_not_logged_in(self):
        self.client.logout()
        response = self.client.get(self._inv_url(view="list"))
        expected = (
            f"{reverse('login')}?next={quote(self._inv_url(view='list'), safe='')}"
        )
        self.assertRedirects(response, expected)

    # --- List view ---

    def test_inventory_list_view(self):
        response = self.client.get(self._inv_url(view="list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/home.html")

    def test_inventory_stats_with_stock(self):
        response = self.client.get(self._inv_url(view="list"))
        stats = response.context["inventory_stats"]
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["with_stock"], 1)
        self.assertEqual(stats["out_of_stock"], 1)

    def test_inventory_list_shows_products(self):
        response = self.client.get(self._inv_url(view="list"))
        products = list(response.context["inventory_page"].object_list)
        self.assertEqual(len(products), 2)
        self.assertIn(self.product_1, products)
        self.assertIn(self.product_2, products)

    def test_inventory_list_context_vars(self):
        response = self.client.get(self._inv_url(view="list"))
        self.assertIn("inventory_page", response.context)
        self.assertIn("inventory_stats", response.context)
        self.assertIn("inventory_action", response.context)
        self.assertEqual(response.context["active_section"], "inventory")
        self.assertEqual(response.context["quick_view"], "list")

    def test_inventory_list_only_shows_products(self):
        CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Corte premium",
            price=Decimal("100.00"),
            sku="SRV100",
        )
        response = self.client.get(self._inv_url(view="list"))
        products = list(response.context["inventory_page"].object_list)
        for p in products:
            self.assertEqual(p.kind, CatalogItem.Kind.PRODUCT)
        self.assertEqual(len(products), 2)

    def test_inventory_pagination(self):
        for i in range(12):
            CatalogItem.objects.create(
                kind=CatalogItem.Kind.PRODUCT,
                name=f"Producto {i}",
                price=Decimal("50.00"),
                sku=f"PRD{i:04d}",
            )
        response = self.client.get(self._inv_url(page=1))
        self.assertEqual(response.status_code, 200)
        products = response.context["inventory_page"]
        self.assertLessEqual(len(list(products.object_list)), 10)

    def test_inventory_pagination_page_2(self):
        for i in range(12):
            CatalogItem.objects.create(
                kind=CatalogItem.Kind.PRODUCT,
                name=f"Producto {i}",
                price=Decimal("50.00"),
                sku=f"PRD{i:04d}",
            )
        response = self.client.get(self._inv_url(page=2))
        self.assertEqual(response.status_code, 200)
        products = response.context["inventory_page"]
        self.assertEqual(len(list(products.object_list)), 4)

    def test_inventory_empty_stats_no_products(self):
        CatalogItem.objects.filter(kind=CatalogItem.Kind.PRODUCT).delete()
        response = self.client.get(self._inv_url(view="list"))
        stats = response.context["inventory_stats"]
        self.assertEqual(stats["total"], 0)
        self.assertEqual(stats["with_stock"], 0)
        self.assertEqual(stats["out_of_stock"], 0)

    # --- Form GET ---

    def test_inventory_form_get_default_adjust(self):
        response = self.client.get(self._inv_url(view="form"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        form = response.context["form"]
        self.assertIsNotNone(form)
        self.assertIn("is_supply", form.fields)
        self.assertIn("quantity", form.fields)

    def test_inventory_purchase_form_get(self):
        response = self.client.get(
            self._inv_url(view="form", inventory_action="purchase"),
        )
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIn("unit_cost", form.fields)
        self.assertNotIn("is_supply", form.fields)

    def test_inventory_adjust_form_get(self):
        response = self.client.get(
            self._inv_url(view="form", inventory_action="adjust"),
        )
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIn("is_supply", form.fields)
        self.assertNotIn("unit_cost", form.fields)

    # --- Purchase POST ---

    def test_inventory_purchase_post_success(self):
        data = {
            "section": "inventory",
            "action": "purchase",
            "product": self.product_2.pk,
            "quantity": "15",
            "unit_cost": "80.00",
            "notes": "Compra de prueba",
        }
        response = self.client.post(self.list_url, data)
        self.assertRedirects(response, f"{self.list_url}?section=inventory&view=list")

    def test_inventory_purchase_increments_stock(self):
        initial_stock = self.product_2.current_stock
        data = {
            "section": "inventory",
            "action": "purchase",
            "product": self.product_2.pk,
            "quantity": "15",
            "unit_cost": "80.00",
        }
        self.client.post(self.list_url, data)
        self.product_2.refresh_from_db()
        self.assertEqual(self.product_2.current_stock, initial_stock + 15)

    def test_inventory_purchase_multiple_times_accumulates(self):
        for qty in ["5", "10", "3"]:
            data = {
                "section": "inventory",
                "action": "purchase",
                "product": self.product_2.pk,
                "quantity": qty,
                "unit_cost": "50.00",
            }
            self.client.post(self.list_url, data)
        self.product_2.refresh_from_db()
        self.assertEqual(self.product_2.current_stock, 18)

    def test_inventory_purchase_creates_movement(self):
        data = {
            "section": "inventory",
            "action": "purchase",
            "product": self.product_1.pk,
            "quantity": "10",
            "unit_cost": "50.00",
            "notes": "Compra test",
        }
        self.client.post(self.list_url, data)
        movements = InventoryMovement.objects.filter(
            product=self.product_1,
            movement_type=InventoryMovement.MovementType.PURCHASE,
        )
        self.assertEqual(movements.count(), 1)
        movement = movements.first()
        self.assertEqual(movement.quantity, 10)
        self.assertEqual(movement.unit_cost, Decimal("50.00"))
        self.assertEqual(movement.notes, "Compra test")
        self.assertEqual(movement.created_by, self.user)

    def test_inventory_purchase_post_invalid_empty_product(self):
        data = {
            "section": "inventory",
            "action": "purchase",
            "product": "",
            "quantity": "",
        }
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("inventory_purchase_form", response.context)
        self.assertIsNotNone(response.context["inventory_purchase_form"])

    def test_inventory_purchase_form_product_queryset_only_products(self):
        response = self.client.get(
            self._inv_url(view="form", inventory_action="purchase"),
        )
        form = response.context["form"]
        qs = form.fields["product"].queryset
        for item in qs:
            self.assertEqual(item.kind, CatalogItem.Kind.PRODUCT)
        self.assertNotIn(self.service_item, qs)

    # --- Adjust POST ---

    def test_inventory_adjust_post_increases_stock(self):
        initial_stock = self.product_1.current_stock
        data = {
            "section": "inventory",
            "action": "adjust",
            "product": self.product_1.pk,
            "quantity": "5",
            "notes": "Ajuste positivo",
        }
        self.client.post(self.list_url, data)
        self.product_1.refresh_from_db()
        self.assertEqual(self.product_1.current_stock, initial_stock + 5)

    def test_inventory_adjust_post_decreases_stock(self):
        initial_stock = self.product_1.current_stock
        data = {
            "section": "inventory",
            "action": "adjust",
            "product": self.product_1.pk,
            "quantity": "-8",
            "notes": "Ajuste negativo",
        }
        self.client.post(self.list_url, data)
        self.product_1.refresh_from_db()
        self.assertEqual(self.product_1.current_stock, initial_stock - 8)

    def test_inventory_adjust_negative_stock_allowed(self):
        data = {
            "section": "inventory",
            "action": "adjust",
            "product": self.product_2.pk,
            "quantity": "-5",
            "notes": "Stock negativo",
        }
        self.client.post(self.list_url, data)
        self.product_2.refresh_from_db()
        self.assertEqual(self.product_2.current_stock, -5)

    def test_inventory_adjust_post_creates_movement(self):
        data = {
            "section": "inventory",
            "action": "adjust",
            "product": self.product_1.pk,
            "quantity": "3",
            "notes": "Ajuste de control",
        }
        self.client.post(self.list_url, data)
        movements = InventoryMovement.objects.filter(
            product=self.product_1,
            movement_type=InventoryMovement.MovementType.ADJUSTMENT,
        )
        self.assertEqual(movements.count(), 1)
        movement = movements.first()
        self.assertEqual(movement.quantity, 3)
        self.assertEqual(movement.notes, "Ajuste de control")
        self.assertEqual(movement.created_by, self.user)
        self.assertFalse(movement.is_supply)

    def test_inventory_adjust_post_invalid_empty_product(self):
        data = {
            "section": "inventory",
            "action": "adjust",
            "product": "",
            "quantity": "",
        }
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("inventory_adjust_form", response.context)

    def test_inventory_adjust_form_product_queryset_only_products(self):
        response = self.client.get(
            self._inv_url(view="form", inventory_action="adjust"),
        )
        form = response.context["form"]
        qs = form.fields["product"].queryset
        for item in qs:
            self.assertEqual(item.kind, CatalogItem.Kind.PRODUCT)
        self.assertNotIn(self.service_item, qs)

    # --- Adjust with is_supply ---

    def test_inventory_adjust_supply_negates_quantity(self):
        data = {
            "section": "inventory",
            "action": "adjust",
            "product": self.product_1.pk,
            "quantity": "10",
            "is_supply": "on",
            "notes": "Insumo empresa",
        }
        self.client.post(self.list_url, data)
        movements = InventoryMovement.objects.filter(
            product=self.product_1,
            movement_type=InventoryMovement.MovementType.ADJUSTMENT,
        )
        movement = movements.first()
        self.assertEqual(movement.quantity, -10)
        self.assertTrue(movement.is_supply)
        self.assertEqual(movement.notes, "Insumo empresa")
        self.product_1.refresh_from_db()
        self.assertEqual(self.product_1.current_stock, 10)

    def test_inventory_adjust_supply_with_negative_input_double_negates(self):
        data = {
            "section": "inventory",
            "action": "adjust",
            "product": self.product_1.pk,
            "quantity": "-10",
            "is_supply": "on",
            "notes": "Insumo",
        }
        self.client.post(self.list_url, data)
        movements = InventoryMovement.objects.filter(
            product=self.product_1,
            movement_type=InventoryMovement.MovementType.ADJUSTMENT,
        )
        movement = movements.first()
        self.assertEqual(movement.quantity, -10)
        self.product_1.refresh_from_db()
        self.assertEqual(self.product_1.current_stock, 10)

    # --- Auto-decrement on product sale create ---

    def test_product_sale_auto_decrements_stock(self):
        initial_stock = self.product_1.current_stock
        data = {
            "section": "sales",
            "type": "producto",
            "product": self.product_1.pk,
            "quantity": "3",
            "product_price": "300.00",
        }
        self.client.post(self.list_url, data)
        self.product_1.refresh_from_db()
        self.assertEqual(self.product_1.current_stock, initial_stock - 3)

    def test_product_sale_with_multiple_quantity_decrements_accordingly(self):
        initial_stock = self.product_1.current_stock
        data = {
            "section": "sales",
            "type": "producto",
            "product": self.product_1.pk,
            "quantity": "7",
            "product_price": "700.00",
        }
        self.client.post(self.list_url, data)
        self.product_1.refresh_from_db()
        self.assertEqual(self.product_1.current_stock, initial_stock - 7)

    def test_product_sale_creates_sale_movement(self):
        data = {
            "section": "sales",
            "type": "producto",
            "product": self.product_1.pk,
            "quantity": "2",
            "product_price": "200.00",
        }
        self.client.post(self.list_url, data)
        movements = InventoryMovement.objects.filter(
            product=self.product_1,
            movement_type=InventoryMovement.MovementType.SALE,
        )
        self.assertEqual(movements.count(), 1)
        movement = movements.first()
        self.assertEqual(movement.quantity, -2)
        self.assertIsNotNone(movement.reference_sale)
        self.assertEqual(movement.created_by, self.user)

    def test_product_sale_creates_sale_movement_with_correct_reference(self):
        data = {
            "section": "sales",
            "type": "producto",
            "product": self.product_1.pk,
            "quantity": "1",
            "product_price": "100.00",
            "notes": "Venta test",
        }
        self.client.post(self.list_url, data)
        record = Sale.objects.get(notes="Venta test")
        movements = InventoryMovement.objects.filter(
            product=self.product_1,
            movement_type=InventoryMovement.MovementType.SALE,
        )
        movement = movements.first()
        self.assertEqual(movement.reference_sale, record)

    def test_service_sale_does_not_affect_stock(self):
        initial_stock = self.product_1.current_stock
        data = {
            "section": "sales",
            "employee": self.employee.pk,
            "product": self.service_item.pk,
            "scheduled_for": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
            "product_price": "60.00",
            "commission_amount": "12.00",
        }
        self.client.post(self.list_url, data)
        self.product_1.refresh_from_db()
        self.assertEqual(self.product_1.current_stock, initial_stock)

    def test_product_sale_decrements_product_stock_not_other_products(self):
        self.product_1.current_stock = 20
        self.product_1.save()
        self.product_2.current_stock = 10
        self.product_2.save()
        data = {
            "section": "sales",
            "type": "producto",
            "product": self.product_1.pk,
            "quantity": "5",
            "product_price": "500.00",
        }
        self.client.post(self.list_url, data)
        self.product_2.refresh_from_db()
        self.assertEqual(self.product_2.current_stock, 10)

    # --- Auto-decrement on product sale edit ---

    def test_product_edit_increases_stock_when_quantity_decreased(self):
        record = Sale.objects.create(
            product=self.product_1,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("500.00"),
            quantity=5,
        )
        data = {
            "action": "update",
            "section": "sales",
            "sale_id": record.pk,
            "product": self.product_1.pk,
            "quantity": "3",
            "product_price": "300.00",
        }
        self.client.post(self.list_url, data)
        self.product_1.refresh_from_db()
        self.assertEqual(self.product_1.current_stock, 22)

    def test_product_edit_decreases_stock_when_quantity_increased(self):
        record = Sale.objects.create(
            product=self.product_1,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("200.00"),
            quantity=2,
        )
        data = {
            "action": "update",
            "section": "sales",
            "sale_id": record.pk,
            "product": self.product_1.pk,
            "quantity": "5",
            "product_price": "500.00",
        }
        self.client.post(self.list_url, data)
        self.product_1.refresh_from_db()
        self.assertEqual(self.product_1.current_stock, 17)

    def test_product_edit_creates_adjustment_movement(self):
        record = Sale.objects.create(
            product=self.product_1,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("200.00"),
            quantity=2,
        )
        data = {
            "action": "update",
            "section": "sales",
            "sale_id": record.pk,
            "product": self.product_1.pk,
            "quantity": "4",
            "product_price": "400.00",
        }
        self.client.post(self.list_url, data)
        movements = InventoryMovement.objects.filter(
            product=self.product_1,
            movement_type=InventoryMovement.MovementType.ADJUSTMENT,
        )
        self.assertEqual(movements.count(), 1)
        movement = movements.first()
        self.assertEqual(movement.quantity, -2)
        self.assertEqual(movement.reference_sale, record)
        self.assertEqual(movement.notes, "Ajuste por modificación de venta")

    def test_product_edit_no_movement_when_quantity_unchanged(self):
        record = Sale.objects.create(
            product=self.product_1,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("300.00"),
            quantity=3,
        )
        data = {
            "action": "update",
            "section": "sales",
            "sale_id": record.pk,
            "product": self.product_1.pk,
            "quantity": "3",
            "product_price": "300.00",
        }
        self.client.post(self.list_url, data)
        movements = InventoryMovement.objects.filter(
            product=self.product_1,
            movement_type=InventoryMovement.MovementType.ADJUSTMENT,
        )
        self.assertEqual(movements.count(), 0)

    def test_product_edit_quantity_from_1_to_1_no_change(self):
        record = Sale.objects.create(
            product=self.product_1,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("100.00"),
            quantity=1,
        )
        initial_stock = self.product_1.current_stock
        data = {
            "action": "update",
            "section": "sales",
            "sale_id": record.pk,
            "product": self.product_1.pk,
            "quantity": "1",
            "product_price": "100.00",
        }
        self.client.post(self.list_url, data)
        self.product_1.refresh_from_db()
        self.assertEqual(self.product_1.current_stock, initial_stock)
        movements = InventoryMovement.objects.filter(
            product=self.product_1,
            movement_type=InventoryMovement.MovementType.ADJUSTMENT,
        )
        self.assertEqual(movements.count(), 0)

    def test_product_edit_quantity_to_zero(self):
        record = Sale.objects.create(
            product=self.product_1,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("300.00"),
            quantity=3,
        )
        data = {
            "action": "update",
            "section": "sales",
            "sale_id": record.pk,
            "product": self.product_1.pk,
            "quantity": "0",
            "product_price": "0.00",
        }
        self.client.post(self.list_url, data)
        self.product_1.refresh_from_db()
        self.assertEqual(self.product_1.current_stock, 23)

    # --- Inventory section context for barbero user ---

    def test_menu_includes_inventory(self):
        response = self.client.get(self._inv_url(view="list"))
        menu = response.context["menu_items"]
        keys = [m["key"] for m in menu]
        self.assertIn("inventory", keys)


class InventoryBarberoAccessTest(TestCase):
    def setUp(self):
        self.barbero_user = User.objects.create_user(
            username="barbero_inv",
            password="pass1234",
            role=User.Role.BARBERO,
        )
        Employee.objects.create(
            user=self.barbero_user,
            full_name="Barbero Inventario",
            document_id="DOC300",
            phone="70000030",
        )
        CatalogItem.objects.create(
            kind=CatalogItem.Kind.PRODUCT,
            name="Gel",
            price=Decimal("80.00"),
            sku="PRD080",
        )
        self.list_url = reverse("dashboard:home")
        self.client.login(username="barbero_inv", password="pass1234")

    def test_barbero_can_access_inventory_list(self):
        response = self.client.get(f"{self.list_url}?section=inventory&view=list")
        self.assertEqual(response.status_code, 200)

    def test_barbero_can_access_inventory_form(self):
        response = self.client.get(
            f"{self.list_url}?section=inventory&view=form&inventory_action=purchase",
        )
        self.assertEqual(response.status_code, 200)

    def test_barbero_stats_visible(self):
        response = self.client.get(f"{self.list_url}?section=inventory&view=list")
        self.assertIn("inventory_stats", response.context)

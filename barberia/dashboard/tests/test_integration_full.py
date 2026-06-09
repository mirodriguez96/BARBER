import json
from datetime import datetime, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from barberia.accounts.models import User
from barberia.catalog.models import CatalogItem
from barberia.common.models import Company
from barberia.dashboard.models import RoleCrudPermission, RoleMenuPermission
from barberia.inventory.models import InventoryMovement
from barberia.operations.models import Purchase, Sale
from barberia.people.models import Client, Employee
from barberia.routers import set_current_db_name


class CrossAppEndToEndTest(TestCase):
    """Complete business flow: create people -> catalog -> purchase -> sell -> verify inventory & overview."""

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

    def tearDown(self):
        set_current_db_name(None)

    def _now_str(self):
        return timezone.localtime().strftime("%Y-%m-%dT%H:%M")

    def test_full_business_flow(self):
        # ====== STEP 1: Create a barber ======
        barber_user = User.objects.create_user(
            username="end_to_end_barber",
            password="pass1234",
            role=User.Role.BARBERO,
        )
        response = self.client.post(
            self.url,
            {
                "section": "barbers",
                "user": barber_user.pk,
                "role": User.Role.BARBERO,
                "full_name": "Barber E2E",
                "document_id": "E2E-BARBER",
                "phone": "700000100",
                "is_active": "on",
            },
        )
        self.assertRedirects(response, f"{self.url}?section=barbers")
        barber = Employee.objects.get(document_id="E2E-BARBER")

        # ====== STEP 2: Create a client ======
        response = self.client.post(
            self.url,
            {
                "section": "barbers",
                "type": "cliente",
                "full_name": "Client E2E",
                "document_id": "E2E-CLIENT",
                "phone": "700000101",
            },
        )
        self.assertRedirects(response, f"{self.url}?section=barbers")
        client = Client.objects.get(document_id="E2E-CLIENT")

        # ====== STEP 3: Create a service in catalog ======
        response = self.client.post(
            self.url,
            {
                "section": "catalog",
                "name": "Corte E2E",
                "kind": CatalogItem.Kind.SERVICE,
                "price": "75.00",
                "barber_commission_percent": "20.00",
                "duration_minutes": "30",
                "is_active": True,
            },
        )
        self.assertRedirects(response, f"{self.url}?section=catalog&view=list")
        service = CatalogItem.objects.get(name="Corte E2E")

        # ====== STEP 4: Create a product in catalog ======
        response = self.client.post(
            self.url,
            {
                "section": "catalog",
                "name": "Producto E2E",
                "kind": CatalogItem.Kind.PRODUCT,
                "price": "35.00",
                "current_stock": "0",
                "is_active": True,
            },
        )
        self.assertRedirects(response, f"{self.url}?section=catalog&view=list")
        product = CatalogItem.objects.get(name="Producto E2E")
        self.assertEqual(product.current_stock, 0)
        self.assertEqual(product.barber_commission_percent, Decimal("0.00"))

        # ====== STEP 5: Purchase the product (stock should increase) ======
        response = self.client.post(
            self.url,
            {
                "section": "compras",
                "action": "save",
                "product": product.pk,
                "quantity": "50",
                "unit_cost": "20.00",
                "notes": "Compra E2E",
            },
        )
        self.assertRedirects(response, f"{self.url}?section=compras&view=list")
        purchase = Purchase.objects.get(notes="Compra E2E")
        product.refresh_from_db()
        self.assertEqual(product.current_stock, 50)

        # Verify inventory movement was created
        self.assertTrue(
            InventoryMovement.objects.filter(
                product=product,
                movement_type=InventoryMovement.MovementType.PURCHASE,
                quantity=50,
                origen=purchase.codigo,
            ).exists()
        )

        # ====== STEP 6: Sell the product (stock should decrease) ======
        response = self.client.post(
            self.url,
            {
                "section": "sales",
                "type": "producto",
                "product": product.pk,
                "quantity": "3",
                "product_price": "35.00",
                "notes": "Venta E2E producto",
            },
        )
        self.assertRedirects(response, f"{self.url}?section=sales")
        product.refresh_from_db()
        self.assertEqual(product.current_stock, 47)

        # Verify sale inventory movement was created
        self.assertTrue(
            InventoryMovement.objects.filter(
                product=product,
                movement_type=InventoryMovement.MovementType.SALE,
                quantity=-3,
            ).exists()
        )

        # ====== STEP 7: Create a service sale ======
        response = self.client.post(
            self.url,
            {
                "section": "sales",
                "employee": barber.pk,
                "client": client.pk,
                "product": service.pk,
                "scheduled_for": self._now_str(),
                "product_price": "75.00",
                "commission_amount": "15.00",
                "tip_amount": "10.00",
                "notes": "Venta E2E servicio",
            },
        )
        self.assertRedirects(response, f"{self.url}?section=sales")
        service_sale = Sale.objects.get(notes="Venta E2E servicio")
        self.assertEqual(service_sale.status, Sale.Status.DONE)

        # ====== STEP 8: Verify the overview stats ======
        response = self.client.get(f"{self.url}?section=overview")
        self.assertEqual(response.status_code, 200)
        overview = response.context["overview_data"]
        self.assertGreaterEqual(overview["sales_period_count"], 2)
        self.assertGreaterEqual(overview["purchases_period_count"], 1)
        self.assertIn("low_stock_count", overview)

        # ====== STEP 9: Verify inventory stats ======
        response = self.client.get(f"{self.url}?section=inventory&view=list")
        self.assertEqual(response.status_code, 200)
        inv_stats = response.context["inventory_stats"]
        self.assertEqual(inv_stats["total"], 1)
        self.assertEqual(inv_stats["with_stock"], 1)
        self.assertEqual(inv_stats["out_of_stock"], 0)

        # ====== STEP 10: Cancel the purchase and verify stock reverts ======
        response = self.client.post(
            self.url,
            {
                "section": "compras",
                "action": "deactivate",
                "purchase_id": str(purchase.pk),
            },
        )
        self.assertRedirects(response, f"{self.url}?section=compras&view=list")
        purchase.refresh_from_db()
        self.assertEqual(purchase.status, Purchase.Status.CANCELED)
        product.refresh_from_db()
        self.assertEqual(product.current_stock, 47 - 50)

        # Verify cancellation movement
        self.assertTrue(
            InventoryMovement.objects.filter(
                product=product,
                notes="Compra anulada",
                quantity=-50,
            ).exists()
        )

    def test_config_company_and_booking(self):
        company_data = {
            "section": "config",
            "config_tab": "company",
            "nit": "123456789",
            "name": "Barbería E2E",
        }
        response = self.client.post(f"{self.url}?section=config", company_data)
        self.assertRedirects(response, f"{self.url}?section=config")

        response = self.client.get(f"{self.url}?section=config&config_tab=company")
        self.assertEqual(response.status_code, 200)
        self.assertIn("company_form", response.context)

        response = self.client.get(f"{self.url}?section=config&config_tab=booking")
        self.assertEqual(response.status_code, 200)
        self.assertIn("booking_form", response.context)

    def test_menu_permissions_configuration(self):
        response = self.client.get(f"{self.url}?section=config&config_tab=permissions")
        self.assertEqual(response.status_code, 200)
        self.assertIn("permission_matrix", response.context)

        post_data = {
            "section": "config",
            "config_tab": "permissions",
            "perms_barbero": ["overview", "barbers", "sales"],
        }
        response = self.client.post(
            f"{self.url}?section=config&config_tab=permissions", post_data
        )
        self.assertRedirects(
            response,
            f"{self.url}?section=config&config_tab=permissions",
        )
        self.assertTrue(
            RoleMenuPermission.objects.filter(
                role=User.Role.BARBERO, menu_key="barbers"
            ).exists()
        )

    def test_crud_permissions_configuration(self):
        response = self.client.get(
            f"{self.url}?section=config&config_tab=crud_permissions"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("crud_section_matrix", response.context)

        post_data = {
            "section": "config",
            "config_tab": "crud_permissions",
            "crud_section": "ventas",
            "crud_barbero_ventas_registrar": "on",
            "crud_barbero_ventas_modificar": "on",
        }
        response = self.client.post(
            f"{self.url}?section=config&config_tab=crud_permissions", post_data
        )
        self.assertRedirects(
            response,
            f"{self.url}?section=config&config_tab=crud_permissions&crud_section=ventas",
        )
        self.assertTrue(
            RoleCrudPermission.objects.filter(
                role=User.Role.BARBERO,
                app_key=RoleCrudPermission.AppKey.VENTAS,
                action=RoleCrudPermission.Action.REGISTRAR,
            ).exists()
        )
        self.assertTrue(
            RoleCrudPermission.objects.filter(
                role=User.Role.BARBERO,
                app_key=RoleCrudPermission.AppKey.VENTAS,
                action=RoleCrudPermission.Action.MODIFICAR,
            ).exists()
        )


class PaymentsIntegrationTest(TestCase):
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
            full_name="Barber Payments",
            document_id="DOC-PAY",
            phone="700000200",
        )
        self.service = CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Corte Payment",
            price=Decimal("60.00"),
            barber_commission_percent=Decimal("25.00"),
            is_active=True,
        )

    def tearDown(self):
        set_current_db_name(None)

    def test_payments_section_shows_commissions_and_tips(self):
        Sale.objects.create(
            employee=self.employee,
            product=self.service,
            performed_by=self.user,
            status=Sale.Status.DONE,
            scheduled_for=timezone.now(),
            product_price=Decimal("60.00"),
            commission_amount=Decimal("15.00"),
            tip_amount=Decimal("5.00"),
        )
        response = self.client.get(f"{self.url}?section=payments")
        self.assertEqual(response.status_code, 200)
        self.assertIn("payments_page", response.context)
        self.assertIn("payments_summary", response.context)
        summary = response.context["payments_summary"]
        self.assertGreaterEqual(summary["total_cuts"], 1)
        self.assertGreaterEqual(summary["commission_total"], Decimal("15.00"))
        self.assertGreaterEqual(summary["tip_total"], Decimal("5.00"))

    def test_payments_no_sales_shows_empty(self):
        response = self.client.get(f"{self.url}?section=payments")
        self.assertEqual(response.status_code, 200)
        page = response.context["payments_page"]
        self.assertEqual(len(list(page.object_list)), 0)


class OverviewIntegrationTest(TestCase):
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
            name="Prod Overview",
            price=Decimal("20.00"),
            current_stock=3,
            is_active=True,
        )
        self.employee = Employee.objects.create(
            user=self.user,
            full_name="Barber Overview",
            document_id="DOC-OV",
            phone="700000300",
        )
        self.service = CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Corte Overview",
            price=Decimal("50.00"),
            barber_commission_percent=Decimal("20.00"),
            is_active=True,
        )

    def tearDown(self):
        set_current_db_name(None)

    def test_overview_metrics(self):
        Sale.objects.create(
            employee=self.employee,
            product=self.service,
            performed_by=self.user,
            status=Sale.Status.DONE,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
        )
        Sale.objects.create(
            product=self.product,
            performed_by=self.user,
            status=Sale.Status.DONE,
            scheduled_for=timezone.now(),
            product_price=Decimal("20.00"),
            quantity=2,
        )
        Purchase.objects.create(
            product=self.product,
            quantity=10,
            unit_cost=Decimal("15.00"),
            created_by=self.user,
        )

        response = self.client.get(f"{self.url}?section=overview")
        self.assertEqual(response.status_code, 200)
        data = response.context["overview_data"]
        self.assertGreaterEqual(data["sales_period_count"], 2)
        self.assertGreaterEqual(data["purchases_period_count"], 1)
        self.assertGreaterEqual(data["sales_period_total"], Decimal("50.00"))
        self.assertGreaterEqual(data["purchases_period_total"], Decimal("150.00"))
        self.assertIn("low_stock_count", data)

    def test_overview_low_stock_detection(self):
        response = self.client.get(f"{self.url}?section=overview")
        self.assertEqual(response.status_code, 200)
        data = response.context["overview_data"]
        self.assertGreaterEqual(data["low_stock_count"], 1)

    def test_overview_period_filter_today(self):
        response = self.client.get(f"{self.url}?section=overview&overview_period=today")
        self.assertEqual(response.status_code, 200)

    def test_overview_period_filter_week(self):
        response = self.client.get(f"{self.url}?section=overview&overview_period=week")
        self.assertEqual(response.status_code, 200)

    def test_overview_period_filter_month(self):
        response = self.client.get(f"{self.url}?section=overview&overview_period=month")
        self.assertEqual(response.status_code, 200)

    def test_overview_chart_data(self):
        Sale.objects.create(
            employee=self.employee,
            product=self.service,
            performed_by=self.user,
            status=Sale.Status.DONE,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
        )
        response = self.client.get(f"{self.url}?section=overview")
        self.assertEqual(response.status_code, 200)
        self.assertIn("daily_cuts_labels_json", response.context)
        self.assertIn("daily_cuts_data_json", response.context)
        self.assertIn("top_services_labels_json", response.context)
        self.assertIn("top_services_data_json", response.context)

    def test_overview_chart_data_multi_day(self):
        today = timezone.now().date()
        for i in range(7):
            Sale.objects.create(
                employee=self.employee,
                product=self.service,
                performed_by=self.user,
                status=Sale.Status.DONE,
                scheduled_for=timezone.make_aware(
                    datetime.combine(today - timedelta(days=i), datetime.min.time())
                ),
                product_price=Decimal("50.00"),
            )
        response = self.client.get(f"{self.url}?section=overview")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.context["top_services_data_json"])
        labels = json.loads(response.context["top_services_labels_json"])
        self.assertGreaterEqual(len(data), 1)
        self.assertIn("Corte Overview", labels)

    def test_top_services_empty_when_no_sales(self):
        response = self.client.get(f"{self.url}?section=overview")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.context["top_services_data_json"])
        self.assertEqual(len(data), 0)


class ConfigInvalidDataTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        set_current_db_name(None)

    def setUp(self):
        set_current_db_name(None)
        self.user = User.objects.create_user(
            username="admin_config",
            password="pass1234",
            role=User.Role.ADMIN,
        )
        self.client.login(username="admin_config", password="pass1234")
        self.url = reverse("dashboard:home")

    def tearDown(self):
        set_current_db_name(None)

    def test_company_form_empty_nit_rejected(self):
        response = self.client.post(
            f"{self.url}?section=config",
            {"section": "config", "config_tab": "company", "nit": "", "name": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("company_form", response.context)
        self.assertTrue(response.context["company_form"].has_error("nit"))

    def test_company_form_redirects_on_success(self):
        response = self.client.post(
            f"{self.url}?section=config",
            {
                "section": "config",
                "config_tab": "company",
                "nit": "456",
                "name": "Test",
            },
        )
        self.assertRedirects(response, f"{self.url}?section=config")
        self.assertTrue(Company.objects.filter(nit="456").exists())

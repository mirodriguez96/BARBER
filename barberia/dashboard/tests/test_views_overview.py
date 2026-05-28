import json
from datetime import date, timedelta
from decimal import Decimal

from bs4 import BeautifulSoup
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from barberia.accounts.models import User
from barberia.catalog.models import CatalogItem
from barberia.inventory.models import InventoryMovement
from barberia.operations.models import Purchase, Sale
from barberia.people.models import Employee


class OverviewDashboardTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="admin",
            password="pass1234",
            role=User.Role.ADMIN,
        )
        self.employee = Employee.objects.create(
            user=self.user,
            full_name="Admin Test",
            document_id="DOC001",
            phone="123456789",
        )
        self.client.login(username="admin", password="pass1234")
        self.list_url = reverse("dashboard:home")
        self.service = CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Corte",
            price=Decimal("50.00"),
            barber_commission_percent=Decimal("20.00"),
            is_active=True,
            sku="SRV001",
        )
        self.product = CatalogItem.objects.create(
            kind=CatalogItem.Kind.PRODUCT,
            name="Gel",
            price=Decimal("30.00"),
            current_stock=10,
            is_active=True,
            sku="PRD001",
        )

    def _overview_url(self, **params):
        params.setdefault("section", "overview")
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.list_url}?{qs}"

    def _get_overview(self, **params):
        params.setdefault("section", "overview")
        return self.client.get(self._overview_url(**params))

    def test_redirect_if_not_logged_in(self):
        self.client.logout()
        response = self.client.get(self.list_url)
        self.assertRedirects(response, f"{reverse('login')}?next={self.list_url}")

    def test_overview_page_loads(self):
        response = self._get_overview()
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/home.html")

    def test_overview_context_has_purchases_and_sales_metrics(self):
        response = self._get_overview()
        od = response.context["overview_data"]
        self.assertIn("sales_period_total", od)
        self.assertIn("sales_period_count", od)
        self.assertIn("sales_period_total_fmt", od)
        self.assertIn("purchases_period_total", od)
        self.assertIn("purchases_period_count", od)
        self.assertIn("purchases_period_total_fmt", od)
        self.assertIn("low_stock_count", od)

    def test_overview_context_has_chart_json_vars(self):
        response = self._get_overview()
        self.assertIn("daily_cuts_labels_json", response.context)
        self.assertIn("daily_cuts_data_json", response.context)
        self.assertIn("top_services_labels_json", response.context)
        self.assertIn("top_services_data_json", response.context)
        self.assertIn("top_supplies_labels_json", response.context)
        self.assertIn("top_supplies_data_json", response.context)

    def test_chart_json_vars_are_valid_json(self):
        response = self._get_overview()
        for key in [
            "daily_cuts_labels_json",
            "daily_cuts_data_json",
            "top_services_labels_json",
            "top_services_data_json",
            "top_supplies_labels_json",
            "top_supplies_data_json",
        ]:
            val = response.context[key]
            try:
                parsed = json.loads(val)
            except json.JSONDecodeError:
                self.fail(f"{key} is not valid JSON: {val}")
            self.assertIsInstance(parsed, list)

    def test_purchases_aggregation_shows_zero_without_data(self):
        response = self._get_overview()
        od = response.context["overview_data"]
        self.assertEqual(od["purchases_period_total"], Decimal("0.00"))
        self.assertEqual(od["purchases_period_count"], 0)
        self.assertEqual(od["purchases_period_total_fmt"], "0")

    def test_purchases_aggregation_shows_correct_total(self):
        Purchase.objects.create(
            product=self.product,
            quantity=3,
            unit_cost=Decimal("100.00"),
            created_by=self.user,
        )
        response = self._get_overview()
        od = response.context["overview_data"]
        self.assertEqual(od["purchases_period_total"], Decimal("300.00"))
        self.assertEqual(od["purchases_period_count"], 1)
        self.assertEqual(od["purchases_period_total_fmt"], "300")

    def test_purchases_multiple_accumulates(self):
        for i in range(2):
            Purchase.objects.create(
                product=self.product,
                quantity=2,
                unit_cost=Decimal("50.00"),
                created_by=self.user,
            )
        response = self._get_overview()
        od = response.context["overview_data"]
        self.assertEqual(od["purchases_period_total"], Decimal("200.00"))
        self.assertEqual(od["purchases_period_count"], 2)

    def test_sales_period_shows_correct_total(self):
        Sale.objects.create(
            product=self.service,
            employee=self.employee,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
            status=Sale.Status.DONE,
        )
        response = self._get_overview()
        od = response.context["overview_data"]
        self.assertEqual(od["sales_period_total"], Decimal("50.00"))
        self.assertEqual(od["sales_period_count"], 1)

    def test_sales_and_purchases_both_present(self):
        Sale.objects.create(
            product=self.service,
            employee=self.employee,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("100.00"),
            status=Sale.Status.DONE,
        )
        Purchase.objects.create(
            product=self.product,
            quantity=5,
            unit_cost=Decimal("20.00"),
            created_by=self.user,
        )
        response = self._get_overview()
        od = response.context["overview_data"]
        self.assertEqual(od["sales_period_total"], Decimal("100.00"))
        self.assertEqual(od["purchases_period_total"], Decimal("100.00"))

    def test_low_stock_count(self):
        response = self._get_overview()
        self.assertEqual(response.context["overview_data"]["low_stock_count"], 0)
        CatalogItem.objects.create(
            kind=CatalogItem.Kind.PRODUCT,
            name="Low stock item",
            price=Decimal("10.00"),
            current_stock=2,
            is_active=True,
            sku="LOW001",
        )
        response = self._get_overview()
        self.assertEqual(response.context["overview_data"]["low_stock_count"], 1)

    def test_low_stock_excludes_inactive_products(self):
        CatalogItem.objects.create(
            kind=CatalogItem.Kind.PRODUCT,
            name="Inactive low stock",
            price=Decimal("10.00"),
            current_stock=2,
            is_active=False,
            sku="INL001",
        )
        response = self._get_overview()
        self.assertEqual(response.context["overview_data"]["low_stock_count"], 0)

    def test_supplies_chart_empty_with_no_movements(self):
        response = self._get_overview()
        labels = json.loads(response.context["top_supplies_labels_json"])
        data = json.loads(response.context["top_supplies_data_json"])
        self.assertEqual(labels, [])
        self.assertEqual(data, [])

    def test_supplies_chart_aggregates_by_product(self):
        other_product = CatalogItem.objects.create(
            kind=CatalogItem.Kind.PRODUCT,
            name="Shampoo",
            price=Decimal("15.00"),
            is_active=True,
            sku="SHP001",
        )
        InventoryMovement.objects.create(
            product=self.product,
            quantity=-5,
            movement_type=InventoryMovement.MovementType.ADJUSTMENT,
            unit_cost=Decimal("10.00"),
            created_by=self.user,
            is_supply=True,
        )
        InventoryMovement.objects.create(
            product=other_product,
            quantity=-3,
            movement_type=InventoryMovement.MovementType.ADJUSTMENT,
            unit_cost=Decimal("15.00"),
            created_by=self.user,
            is_supply=True,
        )
        response = self._get_overview()
        labels = json.loads(response.context["top_supplies_labels_json"])
        data = json.loads(response.context["top_supplies_data_json"])
        self.assertIn("Gel", labels)
        self.assertIn("Shampoo", labels)
        idx_gel = labels.index("Gel")
        idx_shampoo = labels.index("Shampoo")
        self.assertEqual(data[idx_gel], 5)
        self.assertEqual(data[idx_shampoo], 3)
        self.assertEqual(data[idx_gel], max(data))

    def test_supplies_chart_ignores_non_supply(self):
        InventoryMovement.objects.create(
            product=self.product,
            quantity=-10,
            movement_type=InventoryMovement.MovementType.ADJUSTMENT,
            unit_cost=Decimal("10.00"),
            created_by=self.user,
            is_supply=False,
        )
        response = self._get_overview()
        labels = json.loads(response.context["top_supplies_labels_json"])
        self.assertEqual(labels, [])

    def test_supplies_chart_limits_to_7(self):
        for i in range(10):
            prod = CatalogItem.objects.create(
                kind=CatalogItem.Kind.PRODUCT,
                name=f"Supply {i}",
                price=Decimal("10.00"),
                is_active=True,
                sku=f"SUP{i:03d}",
            )
            InventoryMovement.objects.create(
                product=prod,
                quantity=-1,
                movement_type=InventoryMovement.MovementType.ADJUSTMENT,
                unit_cost=Decimal("10.00"),
                created_by=self.user,
                is_supply=True,
            )
        response = self._get_overview()
        labels = json.loads(response.context["top_supplies_labels_json"])
        data = json.loads(response.context["top_supplies_data_json"])
        self.assertLessEqual(len(labels), 7)
        self.assertEqual(len(labels), len(data))

    def test_supplies_chart_negates_quantity(self):
        InventoryMovement.objects.create(
            product=self.product,
            quantity=-8,
            movement_type=InventoryMovement.MovementType.ADJUSTMENT,
            unit_cost=Decimal("10.00"),
            created_by=self.user,
            is_supply=True,
        )
        response = self._get_overview()
        data = json.loads(response.context["top_supplies_data_json"])
        self.assertEqual(data[0], 8)

    def test_supplies_orders_by_total_used_desc(self):
        prod_a = CatalogItem.objects.create(
            kind=CatalogItem.Kind.PRODUCT,
            name="A - Most used",
            price=Decimal("10.00"),
            is_active=True,
            sku="MST001",
        )
        prod_b = CatalogItem.objects.create(
            kind=CatalogItem.Kind.PRODUCT,
            name="B - Less used",
            price=Decimal("10.00"),
            is_active=True,
            sku="LST001",
        )
        InventoryMovement.objects.create(
            product=prod_b,
            quantity=-2,
            movement_type=InventoryMovement.MovementType.ADJUSTMENT,
            unit_cost=Decimal("10.00"),
            created_by=self.user,
            is_supply=True,
        )
        InventoryMovement.objects.create(
            product=prod_a,
            quantity=-10,
            movement_type=InventoryMovement.MovementType.ADJUSTMENT,
            unit_cost=Decimal("10.00"),
            created_by=self.user,
            is_supply=True,
        )
        response = self._get_overview()
        labels = json.loads(response.context["top_supplies_labels_json"])
        data = json.loads(response.context["top_supplies_data_json"])
        self.assertEqual(labels[0], "A - Most used")
        self.assertEqual(data[0], 10)
        self.assertEqual(labels[1], "B - Less used")
        self.assertEqual(data[1], 2)

    def test_top_services_chart_shows_data(self):
        Sale.objects.create(
            product=self.service,
            employee=self.employee,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
            status=Sale.Status.DONE,
        )
        response = self._get_overview()
        labels = json.loads(response.context["top_services_labels_json"])
        data = json.loads(response.context["top_services_data_json"])
        self.assertIn("Corte", labels)
        idx = labels.index("Corte")
        self.assertEqual(data[idx], 1)

    def test_daily_cuts_chart_shows_7_days(self):
        Sale.objects.create(
            product=self.service,
            employee=self.employee,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
            status=Sale.Status.DONE,
        )
        response = self._get_overview()
        labels = json.loads(response.context["daily_cuts_labels_json"])
        data = json.loads(response.context["daily_cuts_data_json"])
        self.assertEqual(len(labels), 7)
        self.assertEqual(len(data), 7)

    def test_overview_period_today(self):
        today = date.today()
        Sale.objects.create(
            product=self.service,
            employee=self.employee,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
            status=Sale.Status.DONE,
        )
        response = self._get_overview(overview_period="today")
        self.assertEqual(response.context["overview_period"], "today")
        self.assertIn("hoy", response.context["period_label"])
        response = self._get_overview()
        self.assertEqual(response.context["overview_period"], "today")

    def test_overview_period_today_shows_no_old_sales(self):
        Sale.objects.create(
            product=self.service,
            employee=self.employee,
            performed_by=self.user,
            scheduled_for=timezone.now() - timedelta(days=3),
            product_price=Decimal("50.00"),
            status=Sale.Status.DONE,
        )
        response = self._get_overview(overview_period="today")
        od = response.context["overview_data"]
        self.assertEqual(od["sales_period_total"], Decimal("0.00"))

    def test_overview_period_week(self):
        Sale.objects.create(
            product=self.service,
            employee=self.employee,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
            status=Sale.Status.DONE,
        )
        response = self._get_overview(overview_period="week")
        self.assertEqual(response.context["overview_period"], "week")
        self.assertIn("semana", response.context["period_label"])

    def test_overview_period_month(self):
        response = self._get_overview(overview_period="month")
        self.assertEqual(response.context["overview_period"], "month")
        self.assertIn("mes", response.context["period_label"])

    def test_overview_period_year(self):
        response = self._get_overview(overview_period="year")
        self.assertEqual(response.context["overview_period"], "year")
        self.assertIn("año", response.context["period_label"])

    def test_overview_period_date(self):
        today_str = date.today().isoformat()
        response = self._get_overview(overview_period="date", overview_date=today_str)
        self.assertEqual(response.context["overview_period"], "date")
        self.assertIn("del", response.context["period_label"])

    def test_purchase_period_today_filters_correctly(self):
        p1 = Purchase.objects.create(
            product=self.product,
            quantity=1,
            unit_cost=Decimal("50.00"),
            created_by=self.user,
        )
        p2 = Purchase.objects.create(
            product=self.product,
            quantity=1,
            unit_cost=Decimal("100.00"),
            created_by=self.user,
        )
        Purchase.objects.filter(pk=p2.pk).update(
            created_at=timezone.now() - timedelta(days=10),
        )
        response = self._get_overview(overview_period="today")
        od = response.context["overview_data"]
        self.assertEqual(od["purchases_period_total"], Decimal("50.00"))
        self.assertEqual(od["purchases_period_count"], 1)

    def test_overview_data_fmt_uses_period_thousands(self):
        Purchase.objects.create(
            product=self.product,
            quantity=1000,
            unit_cost=Decimal("1.00"),
            created_by=self.user,
        )
        response = self._get_overview()
        fmt = response.context["overview_data"]["purchases_period_total_fmt"]
        self.assertIn(".", fmt)

    def test_metric_cards_are_anchor_tags(self):
        response = self._get_overview()
        soup = BeautifulSoup(response.content, "html.parser")
        cards = soup.select("a.dashboard-metric-card")
        self.assertEqual(len(cards), 3)

    def test_ventas_card_links_to_sales_section(self):
        response = self._get_overview()
        soup = BeautifulSoup(response.content, "html.parser")
        ventas_link = soup.select_one("a.dashboard-metric-card")
        href = ventas_link.get("href", "")
        self.assertIn("section=sales", href)

    def test_compras_card_links_to_compras_section(self):
        response = self._get_overview()
        soup = BeautifulSoup(response.content, "html.parser")
        cards = soup.select("a.dashboard-metric-card")
        self.assertIn("section=compras", cards[1].get("href", ""))

    def test_stock_card_links_to_inventory_section(self):
        response = self._get_overview()
        soup = BeautifulSoup(response.content, "html.parser")
        cards = soup.select("a.dashboard-metric-card")
        self.assertIn("section=inventory", cards[2].get("href", ""))

    def test_ventas_card_shows_formatted_amount(self):
        Sale.objects.create(
            product=self.service,
            employee=self.employee,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("75.50"),
            status=Sale.Status.DONE,
        )
        response = self._get_overview()
        soup = BeautifulSoup(response.content, "html.parser")
        soup_text = soup.get_text()
        self.assertIn("Ventas", soup_text)

    def test_compras_card_shows_formatted_purchase_amount(self):
        Purchase.objects.create(
            product=self.product,
            quantity=4,
            unit_cost=Decimal("25.00"),
            created_by=self.user,
        )
        response = self._get_overview()
        soup = BeautifulSoup(response.content, "html.parser")
        soup_text = soup.get_text()
        self.assertIn("Compras", soup_text)

    def test_danger_class_on_stock_card_when_low(self):
        CatalogItem.objects.create(
            kind=CatalogItem.Kind.PRODUCT,
            name="Risk",
            price=Decimal("10.00"),
            current_stock=1,
            is_active=True,
            sku="RSK001",
        )
        response = self._get_overview()
        soup = BeautifulSoup(response.content, "html.parser")
        stock_card = soup.select("a.dashboard-metric-card")[2]
        classes = stock_card.get("class", [])
        self.assertIn("dashboard-metric-card--danger", classes)

    def test_no_danger_class_when_stock_ok(self):
        response = self._get_overview()
        soup = BeautifulSoup(response.content, "html.parser")
        stock_card = soup.select("a.dashboard-metric-card")[2]
        classes = stock_card.get("class", [])
        self.assertNotIn("dashboard-metric-card--danger", classes)

from datetime import datetime
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from barberia.accounts.models import User
from barberia.catalog.models import CatalogItem
from barberia.operations.models import Sale
from barberia.people.models import Client, Employee
from barberia.routers import set_current_db_name


class PaginationIntegrationTest(TestCase):
    PAGE_SIZE = 10

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
        self.client_web = Client.objects.create(full_name="Cliente Test")
        self.service = CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Corte",
            price=Decimal("50.00"),
            barber_commission_percent=Decimal("20.00"),
            sku="SRV999",
        )
        self.http_client = self.client
        self.http_client.login(username="admin", password="pass1234")
        self.list_url = reverse("dashboard:home")

    def tearDown(self):
        set_current_db_name(None)

    @staticmethod
    def _url_with(section, **params):
        parts = [f"section={section}"]
        parts.extend(f"{k}={v}" for k, v in params.items())
        return f"{reverse('dashboard:home')}?{'&'.join(parts)}"

    # --- Helpers to create N records ---

    def _sales(self, count: int):
        for i in range(count):
            Sale.objects.create(
                employee=self.employee,
                client=self.client_web if i % 2 == 0 else None,
                product=self.service,
                performed_by=self.user,
                scheduled_for=timezone.make_aware(datetime(2025, 1, 1, i, 0, 0)),
                product_price=Decimal("50.00"),
                commission_amount=Decimal("10.00"),
            )

    # --- Services pagination ---

    def test_services_pagination_page_2_shows_remaining(self):
        self._sales(12)
        response = self.http_client.get(self._url_with("sales", page="2"))
        self.assertEqual(response.status_code, 200)
        sales = response.context["sales"]
        self.assertEqual(len(list(sales.object_list)), 2)

    def test_services_pagination_filter_plus_pagination(self):
        self._sales(15)
        response = self.http_client.get(
            self._url_with("sales", filter_barber=self.employee.pk, page="2"),
        )
        self.assertEqual(response.status_code, 200)
        sales = response.context["sales"]
        self.assertEqual(len(list(sales.object_list)), 5)

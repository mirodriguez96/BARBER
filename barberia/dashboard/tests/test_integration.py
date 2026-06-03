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

    def _barbers(self, count: int):
        for i in range(count):
            u = User.objects.create_user(
                username=f"barber{i}",
                password="pass1234",
                role=User.Role.BARBERO,
            )
            Employee.objects.create(
                user=u,
                full_name=f"Barber {i}",
                document_id=f"DOC{i:04d}",
                phone=f"700{i:05d}",
            )

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

    # --- Barbers pagination ---

    def test_barber_pagination_page_1_shows_10(self):
        self._barbers(11)
        response = self.http_client.get(self._url_with("barbers", page="1"))
        self.assertEqual(response.status_code, 200)
        barbers = response.context["barbers"]
        self.assertEqual(len(list(barbers.object_list)), self.PAGE_SIZE)

    def test_barber_pagination_page_2_shows_remaining(self):
        self._barbers(10)  # +1 barber +1 client from setUp = 12 total, page 2 = 2
        response = self.http_client.get(self._url_with("barbers", page="2"))
        self.assertEqual(response.status_code, 200)
        barbers = response.context["barbers"]
        self.assertEqual(len(list(barbers.object_list)), 2)

    def test_barber_pagination_no_duplicates_across_pages(self):
        self._barbers(14)  # +1 from setUp = 15 total
        set_current_db_name(None)
        page1 = self.http_client.get(self._url_with("barbers", page="1"))
        set_current_db_name(None)
        page2 = self.http_client.get(self._url_with("barbers", page="2"))
        set_current_db_name(None)
        # Employee and Client share the same auto-increment sequence, so
        # the same pk value can refer to two different records (one of each
        # model). Assert uniqueness on (type, pk) tuples to catch real
        # duplicates from the paginator while tolerating that collision.
        ids_p1 = {(e["type"], e["pk"]) for e in page1.context["barbers"].object_list}
        ids_p2 = {(e["type"], e["pk"]) for e in page2.context["barbers"].object_list}
        self.assertFalse(ids_p1 & ids_p2)

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

    # --- Edge cases ---

    def test_invalid_page_number_returns_first_page(self):
        self._barbers(10)  # +1 from setUp = 11 total
        response = self.http_client.get(self._url_with("barbers", page="abc"))
        self.assertEqual(response.status_code, 200)
        barbers = response.context["barbers"]
        self.assertEqual(len(list(barbers.object_list)), self.PAGE_SIZE)
        self.assertEqual(barbers.number, 1)

    def test_negative_page_returns_last_page(self):
        self._barbers(10)  # +1 barber +1 client from setUp = 12 total, page 2 = 2
        response = self.http_client.get(self._url_with("barbers", page="-1"))
        self.assertEqual(response.status_code, 200)
        barbers = response.context["barbers"]
        self.assertEqual(len(list(barbers.object_list)), 2)
        self.assertEqual(barbers.number, barbers.paginator.num_pages)

    def test_page_too_high_returns_last_page(self):
        self._barbers(10)  # +1 barber +1 client from setUp = 12 total, page 2 = 2
        response = self.http_client.get(self._url_with("barbers", page="999"))
        self.assertEqual(response.status_code, 200)
        barbers = response.context["barbers"]
        self.assertEqual(len(list(barbers.object_list)), 2)
        self.assertEqual(barbers.number, barbers.paginator.num_pages)

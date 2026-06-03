from django.test import TestCase
from django.urls import reverse

from barberia.accounts.models import User
from barberia.people.models import Employee
from barberia.routers import set_current_db_name


class PeoplePaginationTest(TestCase):
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

    # --- Pagination ---

    def test_barber_pagination_page_1_shows_10(self):
        self._barbers(11)
        response = self.http_client.get(self._url_with("barbers", page="1"))
        self.assertEqual(response.status_code, 200)
        barbers = response.context["barbers"]
        self.assertEqual(len(list(barbers.object_list)), self.PAGE_SIZE)

    def test_barber_pagination_page_2_shows_remaining(self):
        self._barbers(11)
        response = self.http_client.get(self._url_with("barbers", page="2"))
        self.assertEqual(response.status_code, 200)
        barbers = response.context["barbers"]
        self.assertEqual(len(list(barbers.object_list)), 1)

    def test_barber_pagination_no_duplicates_across_pages(self):
        self._barbers(15)
        set_current_db_name(None)
        page1 = self.http_client.get(self._url_with("barbers", page="1"))
        set_current_db_name(None)
        page2 = self.http_client.get(self._url_with("barbers", page="2"))
        set_current_db_name(None)
        ids_p1 = {(e["type"], e["pk"]) for e in page1.context["barbers"].object_list}
        ids_p2 = {(e["type"], e["pk"]) for e in page2.context["barbers"].object_list}
        self.assertFalse(ids_p1 & ids_p2)

    # --- Edge cases ---

    def test_invalid_page_number_returns_first_page(self):
        self._barbers(11)
        response = self.http_client.get(self._url_with("barbers", page="abc"))
        self.assertEqual(response.status_code, 200)
        barbers = response.context["barbers"]
        self.assertEqual(len(list(barbers.object_list)), self.PAGE_SIZE)
        self.assertEqual(barbers.number, 1)

    def test_negative_page_returns_last_page(self):
        self._barbers(11)
        response = self.http_client.get(self._url_with("barbers", page="-1"))
        self.assertEqual(response.status_code, 200)
        barbers = response.context["barbers"]
        self.assertEqual(len(list(barbers.object_list)), 1)
        self.assertEqual(barbers.number, barbers.paginator.num_pages)

    def test_page_too_high_returns_last_page(self):
        self._barbers(11)
        response = self.http_client.get(self._url_with("barbers", page="999"))
        self.assertEqual(response.status_code, 200)
        barbers = response.context["barbers"]
        self.assertEqual(len(list(barbers.object_list)), 1)
        self.assertEqual(barbers.number, barbers.paginator.num_pages)

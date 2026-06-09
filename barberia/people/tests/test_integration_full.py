from datetime import datetime
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from barberia.accounts.models import User
from barberia.catalog.models import CatalogItem
from barberia.common.tests.pagination_mixin import PaginationTestMixin
from barberia.dashboard.models import RoleCrudPermission, RoleMenuPermission
from barberia.operations.models import Sale
from barberia.people.models import Client, Employee
from barberia.routers import set_current_db_name


class PeopleFullLifecycleTest(TestCase):
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

    def _list_url(self):
        return f"{self.url}?section=barbers&view=list"

    def _section_url(self):
        return f"{self.url}?section=barbers"

    # --- Barber full lifecycle: create -> edit -> deactivate -> activate ---

    def test_barber_full_lifecycle(self):
        barber_user = User.objects.create_user(
            username="barber_lifecycle",
            password="pass1234",
            role=User.Role.BARBERO,
        )
        create_data = {
            "section": "barbers",
            "user": barber_user.pk,
            "role": User.Role.BARBERO,
            "full_name": "Barber Lifecycle",
            "document_id": "DOC-LIFECYCLE",
            "phone": "700111222",
            "email": "barber@test.com",
            "day_off": "",
            "is_active": True,
        }
        response = self.client.post(self.url, create_data)
        self.assertRedirects(response, self._section_url())
        barber = Employee.objects.get(document_id="DOC-LIFECYCLE")
        self.assertTrue(barber.is_active)
        self.assertEqual(barber.full_name, "Barber Lifecycle")

        edit_data = {
            "section": "barbers",
            "action": "update",
            "barber_id": str(barber.pk),
            "full_name": "Barber Updated",
            "phone": "700333444",
            "email": "updated@test.com",
            "day_off": "",
            "role": User.Role.BARBERO,
        }
        response = self.client.post(self.url, edit_data)
        self.assertRedirects(response, self._list_url())
        barber.refresh_from_db()
        self.assertEqual(barber.full_name, "Barber Updated")
        self.assertEqual(barber.phone, "700333444")

        deactivate_data = {
            "section": "barbers",
            "action": "deactivate",
            "barber_id": str(barber.pk),
        }
        response = self.client.post(self.url, deactivate_data)
        self.assertRedirects(response, self._list_url())
        barber.refresh_from_db()
        self.assertFalse(barber.is_active)

        activate_data = {
            "section": "barbers",
            "action": "activate",
            "barber_id": str(barber.pk),
        }
        response = self.client.post(self.url, activate_data)
        self.assertRedirects(response, self._list_url())
        barber.refresh_from_db()
        self.assertTrue(barber.is_active)

    # --- Client full lifecycle: create -> edit -> deactivate -> activate ---

    def test_client_full_lifecycle(self):
        create_data = {
            "section": "barbers",
            "type": "cliente",
            "full_name": "Client Lifecycle",
            "document_id": "CLI-LIFECYCLE",
            "phone": "700555666",
            "email": "client@test.com",
            "birth_date": "",
            "is_active": True,
        }
        response = self.client.post(self.url, create_data)
        self.assertRedirects(response, self._section_url())
        client = Client.objects.get(document_id="CLI-LIFECYCLE")
        self.assertTrue(client.is_active)
        self.assertEqual(client.full_name, "Client Lifecycle")

        edit_data = {
            "section": "barbers",
            "action": "update",
            "type": "cliente",
            "client_id": str(client.pk),
            "full_name": "Client Updated",
            "document_id": "CLI-LIFECYCLE",
            "phone": "700777888",
            "email": "updated_client@test.com",
            "birth_date": "",
        }
        response = self.client.post(self.url, edit_data)
        self.assertRedirects(response, self._list_url())
        client.refresh_from_db()
        self.assertEqual(client.full_name, "Client Updated")
        self.assertEqual(client.phone, "700777888")

        deactivate_data = {
            "section": "barbers",
            "action": "deactivate",
            "type": "cliente",
            "client_id": str(client.pk),
        }
        response = self.client.post(self.url, deactivate_data)
        self.assertRedirects(response, self._list_url())
        client.refresh_from_db()
        self.assertFalse(client.is_active)

        activate_data = {
            "section": "barbers",
            "action": "activate",
            "type": "cliente",
            "client_id": str(client.pk),
        }
        response = self.client.post(self.url, activate_data)
        self.assertRedirects(response, self._list_url())
        client.refresh_from_db()
        self.assertTrue(client.is_active)

    # --- Duplicate document_id validation ---

    def test_barber_duplicate_document_id_rejected(self):
        Employee.objects.create(
            full_name="Original",
            document_id="DUP-DOC",
            phone="700000001",
        )
        barber_user = User.objects.create_user(
            username="dup_barber",
            password="pass1234",
            role=User.Role.BARBERO,
        )
        data = {
            "section": "barbers",
            "user": barber_user.pk,
            "role": User.Role.BARBERO,
            "full_name": "Duplicate",
            "document_id": "DUP-DOC",
            "phone": "700000002",
            "is_active": True,
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        self.assertTrue(response.context["form"].has_error("document_id"))

    def test_client_duplicate_document_id_rejected(self):
        Client.objects.create(
            full_name="Original Client",
            document_id="DUP-CLI",
            phone="700000003",
        )
        data = {
            "section": "barbers",
            "type": "cliente",
            "full_name": "Duplicate Client",
            "document_id": "DUP-CLI",
            "phone": "700000004",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)

    # --- Permission-based access ---

    def test_barbero_cannot_access_barbers_section_without_menu_permission(self):
        self.client.logout()
        _ = User.objects.create_user(
            username="restricted_barber",
            password="pass1234",
            role=User.Role.BARBERO,
        )
        RoleMenuPermission.objects.create(
            role=User.Role.BARBERO,
            menu_key="overview",
        )
        self.client.login(username="restricted_barber", password="pass1234")
        response = self.client.get(f"{self.url}?section=barbers")
        self.assertRedirects(response, f"{self.url}?section=overview")

    def test_barbero_can_access_barbers_with_permission(self):
        self.client.logout()
        _ = User.objects.create_user(
            username="perm_barber",
            password="pass1234",
            role=User.Role.BARBERO,
        )
        RoleMenuPermission.objects.create(
            role=User.Role.BARBERO,
            menu_key="barbers",
        )
        self.client.login(username="perm_barber", password="pass1234")
        response = self.client.get(f"{self.url}?section=barbers")
        self.assertEqual(response.status_code, 200)

    def test_barbero_cannot_create_barber_without_crud_permission(self):
        self.client.logout()
        _ = User.objects.create_user(
            username="no_crud_barber",
            password="pass1234",
            role=User.Role.BARBERO,
        )
        RoleMenuPermission.objects.create(role=User.Role.BARBERO, menu_key="barbers")
        self.client.login(username="no_crud_barber", password="pass1234")
        data = {
            "section": "barbers",
            "full_name": "Should Not Create",
            "document_id": "NO-CRUD",
            "phone": "700999888",
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, self._list_url())

    def test_barbero_can_create_barber_with_crud_permission(self):
        self.client.logout()
        _ = User.objects.create_user(
            username="crud_barber",
            password="pass1234",
            role=User.Role.BARBERO,
        )
        RoleMenuPermission.objects.create(role=User.Role.BARBERO, menu_key="barbers")
        RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key=RoleCrudPermission.AppKey.PERSONAL,
            action=RoleCrudPermission.Action.REGISTRAR,
        )
        self.client.login(username="crud_barber", password="pass1234")
        barber_user = User.objects.create_user(
            username="new_barber_crud",
            password="pass1234",
            role=User.Role.BARBERO,
        )
        data = {
            "section": "barbers",
            "user": barber_user.pk,
            "role": User.Role.BARBERO,
            "full_name": "CRUD Created",
            "document_id": "CRUD-BARBER",
            "phone": "700000999",
            "is_active": True,
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Employee.objects.filter(document_id="CRUD-BARBER").exists())

    # --- Barber with sales cannot be deleted (FK PROTECT) ---

    def test_barber_with_sales_cannot_be_deactivated_via_protect(self):
        barber_user = User.objects.create_user(
            username="protected_barber",
            password="pass1234",
            role=User.Role.BARBERO,
        )
        barber = Employee.objects.create(
            user=barber_user,
            full_name="Protected Barber",
            document_id="PROTECTED",
            phone="700000000",
        )
        service = CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Test Service",
            price=Decimal("50.00"),
        )
        Sale.objects.create(
            employee=barber,
            product=service,
            performed_by=self.user,
            product_price=Decimal("50.00"),
            scheduled_for=timezone.make_aware(datetime(2025, 1, 1, 0, 0, 0)),
        )

        data = {
            "section": "barbers",
            "action": "deactivate",
            "barber_id": str(barber.pk),
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, self._list_url())
        barber.refresh_from_db()
        self.assertFalse(barber.is_active)

    # --- Duplicate user assignment ---

    def test_barber_cannot_reuse_same_user(self):
        barber_user = User.objects.create_user(
            username="unique_user",
            password="pass1234",
            role=User.Role.BARBERO,
        )
        Employee.objects.create(
            user=barber_user,
            full_name="First Barber",
            document_id="UNIQUE-USER",
            phone="700000001",
        )
        data = {
            "section": "barbers",
            "user": barber_user.pk,
            "role": User.Role.BARBERO,
            "full_name": "Second Barber",
            "document_id": "UNIQUE-USER-2",
            "phone": "700000002",
            "is_active": True,
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)


class PeopleSearchFilterTest(TestCase):
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
        for i in range(5):
            u = User.objects.create_user(
                username=f"barber_search_{i}",
                password="pass1234",
                role=User.Role.BARBERO,
            )
            Employee.objects.create(
                user=u,
                full_name=f"Barber Search {i}",
                document_id=f"SRCH-B{i:04d}",
                phone=f"710{i:05d}",
            )
        for i in range(3):
            Client.objects.create(
                full_name=f"Client Search {i}",
                document_id=f"SRCH-C{i:04d}",
                phone=f"720{i:05d}",
            )

    def tearDown(self):
        set_current_db_name(None)

    def test_search_by_barber_name(self):
        response = self.client.get(
            f"{self.url}?section=barbers&barber_search=Barber+Search+1"
        )
        self.assertEqual(response.status_code, 200)
        people = list(response.context["people_page"].object_list)
        names = [p["full_name"] for p in people]
        self.assertIn("Barber Search 1", names)
        self.assertNotIn("Barber Search 4", names)

    def test_filter_by_type_colaborador(self):
        response = self.client.get(
            f"{self.url}?section=barbers&barber_type=colaborador"
        )
        self.assertEqual(response.status_code, 200)
        people = list(response.context["people_page"].object_list)
        for p in people:
            self.assertEqual(p["type"], "colaborador")

    def test_filter_by_type_cliente(self):
        response = self.client.get(f"{self.url}?section=barbers&barber_type=cliente")
        self.assertEqual(response.status_code, 200)
        people = list(response.context["people_page"].object_list)
        for p in people:
            self.assertEqual(p["type"], "cliente")

    def test_search_with_no_results_shows_empty(self):
        response = self.client.get(
            f"{self.url}?section=barbers&barber_search=XXXXXXXXXX"
        )
        self.assertEqual(response.status_code, 200)
        people = list(response.context["people_page"].object_list)
        self.assertEqual(len(people), 0)

    def test_stats_show_correct_counts(self):
        response = self.client.get(f"{self.url}?section=barbers")
        self.assertEqual(response.status_code, 200)
        stats = response.context["barber_stats"]
        self.assertEqual(stats["barbers"], 5)
        self.assertEqual(stats["clients"], 3)


class PeoplePaginationTest(PaginationTestMixin, TestCase):
    section_name = "barbers"
    context_key = "people_page"

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

    def _create_pagination_items(self, count: int):
        for i in range(count):
            u = User.objects.create_user(
                username=f"pag_barber{i}",
                password="pass1234",
                role=User.Role.BARBERO,
            )
            Employee.objects.create(
                user=u,
                full_name=f"Pagination Barber {i}",
                document_id=f"PAGDOC{i:04d}",
                phone=f"700{i:05d}",
            )

    def _get_item_id(self, item):
        return item["pk"]

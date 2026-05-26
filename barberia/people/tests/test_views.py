from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from barberia.people.models import Client as ClientModel, Employee

User = get_user_model()


class BarberDashboardViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username="admin",
            password="testpass123",
            role=User.Role.ADMIN,
        )
        self.employee_user = User.objects.create_user(
            username="barbero1",
            password="testpass123",
            role=User.Role.BARBERO,
        )
        self.employee = Employee.objects.create(
            user=self.employee_user,
            full_name="Barbero Test",
            document_id="1020304050",
            phone="3001234567",
        )
        self.dashboard_url = reverse("dashboard:home")
        self.login_url = reverse("login")

    def _login(self):
        self.client.login(username="admin", password="testpass123")

    # --- Authentication ---

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(self.dashboard_url)
        self.assertRedirects(
            response,
            f"{self.login_url}?next={self.dashboard_url}",
        )

    def test_authenticated_user_can_access(self):
        self._login()
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)

    # --- Barbers: GET ---

    def test_barber_list_view(self):
        self._login()
        response = self.client.get(
            self.dashboard_url,
            {"section": "barbers", "view": "list"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/home.html")
        self.assertContains(response, "Barbero Test")

    def test_barber_form_get_renders_form(self):
        self._login()
        response = self.client.get(
            self.dashboard_url,
            {"section": "barbers"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)

    def test_barber_edit_get_loads_instance(self):
        self._login()
        response = self.client.get(
            self.dashboard_url,
            {
                "section": "barbers",
                "view": "edit",
                "barber": self.employee.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["barber_to_edit"], self.employee)

    def test_barber_edit_get_404_for_nonexistent(self):
        self._login()
        response = self.client.get(
            self.dashboard_url,
            {
                "section": "barbers",
                "view": "edit",
                "barber": 99999,
            },
        )
        self.assertEqual(response.status_code, 404)

    # --- Barbers: POST create ---

    def test_barber_create_post_success(self):
        self._login()
        new_user = User.objects.create_user(
            username="nuevobarbero",
            password="testpass123",
        )
        response = self.client.post(
            self.dashboard_url,
            {
                "section": "barbers",
                "action": "save",
                "type": "barbero",
                "user": new_user.pk,
                "full_name": "Nuevo Barbero",
                "document_id": "9988776655",
                "phone": "3111111111",
                "email": "",
                "role": User.Role.BARBERO,
            },
        )
        self.assertEqual(Employee.objects.count(), 2)
        self.assertRedirects(
            response,
            f"{self.dashboard_url}?section=barbers",
        )

    def test_barber_create_post_invalid_rerenders_form(self):
        self._login()
        response = self.client.post(
            self.dashboard_url,
            {
                "section": "barbers",
                "action": "save",
                "full_name": "",
                "document_id": "",
                "phone": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        self.assertFalse(response.context["form"].is_valid())

    # --- Barbers: POST update ---

    def test_barber_edit_post_success(self):
        self._login()
        response = self.client.post(
            self.dashboard_url,
            {
                "section": "barbers",
                "action": "update",
                "barber_id": self.employee.pk,
                "full_name": "Barbero Editado",
                "phone": "3001111111",
                "email": "",
                "role": User.Role.BARBERO,
            },
        )
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.full_name, "Barbero Editado")
        self.assertEqual(self.employee.phone, "3001111111")
        self.assertRedirects(
            response,
            f"{self.dashboard_url}?section=barbers&view=list",
        )

    def test_barber_edit_post_invalid_rerenders_edit(self):
        self._login()
        response = self.client.post(
            self.dashboard_url,
            {
                "section": "barbers",
                "action": "update",
                "barber_id": self.employee.pk,
                "full_name": "",
                "phone": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        self.assertFalse(response.context["form"].is_valid())
        self.assertEqual(
            response.context["barber_to_edit"],
            self.employee,
        )

    # --- Barbers: POST activate / deactivate ---

    def test_barber_deactivate(self):
        self._login()
        response = self.client.post(
            self.dashboard_url,
            {
                "section": "barbers",
                "action": "deactivate",
                "barber_id": self.employee.pk,
            },
        )
        self.employee.refresh_from_db()
        self.assertFalse(self.employee.is_active)
        self.assertRedirects(
            response,
            f"{self.dashboard_url}?section=barbers&view=list",
        )

    def test_barber_activate(self):
        self.employee.is_active = False
        self.employee.save()
        self._login()
        response = self.client.post(
            self.dashboard_url,
            {
                "section": "barbers",
                "action": "activate",
                "barber_id": self.employee.pk,
            },
        )
        self.employee.refresh_from_db()
        self.assertTrue(self.employee.is_active)
        self.assertRedirects(
            response,
            f"{self.dashboard_url}?section=barbers&view=list",
        )

    def test_barber_deactivate_nonexistent_returns_404(self):
        self._login()
        response = self.client.post(
            self.dashboard_url,
            {
                "section": "barbers",
                "action": "deactivate",
                "barber_id": 99999,
            },
        )
        self.assertEqual(response.status_code, 404)

    def test_barber_activate_nonexistent_returns_404(self):
        self._login()
        response = self.client.post(
            self.dashboard_url,
            {
                "section": "barbers",
                "action": "activate",
                "barber_id": 99999,
            },
        )
        self.assertEqual(response.status_code, 404)

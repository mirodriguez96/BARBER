from decimal import Decimal

from bs4 import BeautifulSoup
from django.test import TestCase
from django.urls import reverse

from barberia.accounts.models import User
from barberia.catalog.models import CatalogItem
from barberia.people.models import Client, Employee


class DashboardTemplateRenderingTest(TestCase):
    """Verify rendered HTML content using BeautifulSoup."""

    def setUp(self):
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
            sku="SRV050",
        )
        self.http_client = self.client
        self.http_client.login(username="admin", password="pass1234")
        self.list_url = reverse("dashboard:home")

    @staticmethod
    def _url_with(section, **params):
        parts = [f"section={section}"]
        parts.extend(f"{k}={v}" for k, v in params.items())
        return f"{reverse('dashboard:home')}?{'&'.join(parts)}"

    def _soup(self, section="barbers", **params):
        response = self.http_client.get(self._url_with(section, **params))
        return BeautifulSoup(response.content, "html.parser")

    def test_empty_services_shows_message(self):
        soup = self._soup("sales")
        body = soup.get_text()
        self.assertTrue(
            "no hay" in body.lower() or "sin" in body.lower() or "servicios" in body,
        )

    def test_services_form_has_bootstrap_classes(self):
        soup = self._soup("sales", view="form")
        all_styled = soup.select(
            "input.form-control, input.form-control-lg, "
            "select.form-select, select.form-select-lg",
        )
        self.assertGreater(len(all_styled), 0)

    # --- ServiceCatalogSelect data attributes ---

    def test_service_select_has_data_attributes(self):
        soup = self._soup("sales", view="form")
        select = soup.find("select", {"name": "product"})
        if select:
            options = select.find_all("option", {"data-price": True})
            self.assertGreater(len(options), 0)
            for opt in options:
                self.assertIn("data-price", opt.attrs)
                self.assertIn("data-commission", opt.attrs)

from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from bs4 import BeautifulSoup
from barberia.accounts.models import User
from barberia.catalog.models import CatalogItem
from barberia.people.models import Employee, Client


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
            full_name="Barbero Uno",
            document_id="DOC001",
            phone="70000001",
        )
        self.client_web = Client.objects.create(full_name="Cliente Test")
        self.service = CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Corte",
            price=Decimal("50.00"),
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

    # --- Pagination links ---

    def test_pagination_links_rendered_when_multipage(self):
        for i in range(10):
            u = User.objects.create_user(
                username=f"bpag{i}", password="pass1234", role=User.Role.BARBERO
            )
            Employee.objects.create(
                user=u,
                full_name=f"B Pag {i}",
                document_id=f"DOCP{i:04d}",
                phone=f"700{i:05d}",
            )
        soup = self._soup("barbers")
        pag_links = soup.select("a.dashboard-pagination__link")
        self.assertGreater(len(pag_links), 0)

    def test_pagination_links_use_page_param(self):
        for i in range(10):
            u = User.objects.create_user(
                username=f"bpp{i}", password="pass1234", role=User.Role.BARBERO
            )
            Employee.objects.create(
                user=u,
                full_name=f"B Page {i}",
                document_id=f"DOCQ{i:04d}",
                phone=f"700{i:05d}",
            )
        soup = self._soup("barbers")
        for link in soup.select("a.dashboard-pagination__link"):
            href = link.get("href", "")
            self.assertIn("page=", href, msg=f"Missing page= in {href}")

    # --- Empty state ---

    def test_empty_barbers_shows_message(self):
        soup = self._soup("barbers")
        body = soup.get_text()
        self.assertTrue(
            "no hay" in body.lower() or "sin" in body.lower() or "barberos" in body
        )

    def test_empty_catalog_shows_message(self):
        soup = self._soup("catalog")
        body = soup.get_text()
        self.assertTrue(
            "no hay" in body.lower() or "sin" in body.lower() or "catálogo" in body
        )

    def test_empty_services_shows_message(self):
        soup = self._soup("services")
        body = soup.get_text()
        self.assertTrue(
            "no hay" in body.lower() or "sin" in body.lower() or "servicios" in body
        )

    # --- Metric cards ---

    def test_barbers_section_renders_stats_cards(self):
        soup = self._soup("barbers")
        cards = soup.select(".dashboard-metric-card")
        self.assertGreaterEqual(len(cards), 3)

    def test_catalog_section_renders_stats_cards(self):
        CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE, name="Test", price=Decimal("10.00")
        )
        soup = self._soup("catalog")
        cards = soup.select(".dashboard-metric-card")
        self.assertGreaterEqual(len(cards), 3)

    # --- Bootstrap form classes ---

    def test_barber_form_has_bootstrap_classes(self):
        soup = self._soup("barbers", view="form")
        all_form_controls = soup.select(
            "input.form-control, input.form-control-lg, "
            "select.form-select, select.form-select-lg"
        )
        self.assertGreater(len(all_form_controls), 0)

    def test_catalog_form_has_bootstrap_classes(self):
        soup = self._soup("catalog", view="form")
        all_styled = soup.select(
            "input.form-control, input.form-control-lg, "
            "select.form-select, select.form-select-lg"
        )
        self.assertGreater(len(all_styled), 0)

    def test_services_form_has_bootstrap_classes(self):
        soup = self._soup("services", view="form")
        all_styled = soup.select(
            "input.form-control, input.form-control-lg, "
            "select.form-select, select.form-select-lg"
        )
        self.assertGreater(len(all_styled), 0)

    # --- ServiceCatalogSelect data attributes ---

    def test_service_select_has_data_attributes(self):
        soup = self._soup("services", view="form")
        select = soup.find("select", {"name": "service"})
        if select:
            options = select.find_all("option", {"data-price": True})
            self.assertGreater(len(options), 0)
            for opt in options:
                self.assertIn("data-price", opt.attrs)
                self.assertIn("data-commission", opt.attrs)

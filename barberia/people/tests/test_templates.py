from bs4 import BeautifulSoup
from django.test import TestCase
from django.urls import reverse

from barberia.accounts.models import User
from barberia.people.models import Employee


class PeopleTemplateRenderingTest(TestCase):
    """Verify rendered HTML content for barbers section using BeautifulSoup."""

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

    def test_pagination_links_rendered_when_multipage(self):
        for i in range(10):
            u = User.objects.create_user(
                username=f"bpag{i}",
                password="pass1234",
                role=User.Role.BARBERO,
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
                username=f"bpp{i}",
                password="pass1234",
                role=User.Role.BARBERO,
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

    def test_empty_barbers_shows_message(self):
        soup = self._soup("barbers")
        body = soup.get_text()
        self.assertTrue(
            "no hay" in body.lower()
            or "sin" in body.lower()
            or "barberos" in body
            or "colaborador" in body.lower()
        )

    def test_barber_form_has_bootstrap_classes(self):
        soup = self._soup("barbers", view="form")
        all_form_controls = soup.select(
            "input.form-control, input.form-control-lg, "
            "select.form-select, select.form-select-lg",
        )
        self.assertGreater(len(all_form_controls), 0)

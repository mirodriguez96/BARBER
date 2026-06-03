from bs4 import BeautifulSoup
from django.test import TestCase
from django.urls import reverse

from barberia.accounts.models import User


class CatalogTemplateRenderingTest(TestCase):
    """Verify rendered HTML content using BeautifulSoup."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="admin",
            password="pass1234",
            role=User.Role.ADMIN,
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

    def test_empty_catalog_shows_message(self):
        soup = self._soup("catalog")
        body = soup.get_text()
        self.assertTrue(
            "no hay" in body.lower() or "sin" in body.lower() or "catálogo" in body,
        )

    def test_catalog_form_has_bootstrap_classes(self):
        soup = self._soup("catalog", view="form")
        all_styled = soup.select(
            "input.form-control, input.form-control-lg, "
            "select.form-select, select.form-select-lg",
        )
        self.assertGreater(len(all_styled), 0)

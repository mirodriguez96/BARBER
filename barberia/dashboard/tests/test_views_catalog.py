from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from barberia.accounts.models import User
from barberia.catalog.models import CatalogItem


class CatalogDashboardViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="admin",
            password="pass1234",
            role=User.Role.ADMIN,
        )
        self.client.login(username="admin", password="pass1234")
        self.list_url = reverse("dashboard:home")

    def _catalog_url(self, **params):
        params.setdefault("section", "catalog")
        params.setdefault("view", "list")
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.list_url}?{qs}"

    # --- Authentication ---
    def test_redirect_if_not_logged_in(self):
        self.client.logout()
        response = self.client.get(self.list_url)
        self.assertRedirects(response, f"{reverse('login')}?next={self.list_url}")

    # --- List ---
    def test_catalog_list_view(self):
        CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Corte",
            price=Decimal("50.00"),
            sku="SRV050",
        )
        CatalogItem.objects.create(
            kind=CatalogItem.Kind.PRODUCT,
            name="Gel",
            price=Decimal("80.00"),
            sku="PRD080",
        )
        response = self.client.get(self._catalog_url(section="catalog", view="list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/home.html")
        self.assertContains(response, "Corte")
        self.assertContains(response, "Gel")

    # --- Create GET ---
    def test_catalog_form_get(self):
        response = self.client.get(self._catalog_url(section="catalog", view="form"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)

    # --- Create POST ---
    def test_catalog_create_post_success(self):
        data = {
            "section": "catalog",
            "name": "Corte nuevo",
            "kind": CatalogItem.Kind.SERVICE,
            "price": "65.00",
            "barber_commission_percent": "25.00",
            "is_active": True,
            "description": "Nuevo servicio",
        }
        response = self.client.post(self.list_url, data)
        self.assertRedirects(response, f"{self.list_url}?section=catalog")
        self.assertTrue(CatalogItem.objects.filter(name="Corte nuevo").exists())

    def test_catalog_create_post_invalid(self):
        data = {
            "section": "catalog",
            "name": "",
            "kind": "",
            "price": "",
        }
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)

    # --- Edit GET ---
    def test_catalog_edit_get_loads_instance(self):
        item = CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Corte editable",
            price=Decimal("50.00"),
        )
        response = self.client.get(
            self._catalog_url(section="catalog", view="edit", catalog_item=item.pk),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["catalog_item_to_edit"].pk, item.pk)

    def test_catalog_edit_get_404_for_nonexistent(self):
        response = self.client.get(
            self._catalog_url(section="catalog", view="edit", catalog_item=999),
        )
        self.assertEqual(response.status_code, 404)

    # --- Edit POST ---
    def test_catalog_edit_post_success(self):
        item = CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Original",
            price=Decimal("50.00"),
        )
        data = {
            "action": "update",
            "section": "catalog",
            "catalog_item_id": item.pk,
            "name": "Actualizado",
            "kind": CatalogItem.Kind.SERVICE,
            "price": "75.00",
            "barber_commission_percent": "20.00",
            "description": "",
        }
        response = self.client.post(self.list_url, data)
        self.assertRedirects(response, f"{self.list_url}?section=catalog&view=list")
        item.refresh_from_db()
        self.assertEqual(item.name, "Actualizado")
        self.assertEqual(item.price, Decimal("75.00"))

    def test_catalog_edit_post_invalid(self):
        item = CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Original",
            price=Decimal("50.00"),
        )
        data = {
            "action": "update",
            "section": "catalog",
            "catalog_item_id": item.pk,
            "name": "",
            "kind": "",
            "price": "",
        }
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, 200)

    # --- Deactivate / Activate ---
    def test_catalog_deactivate(self):
        item = CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Desactivar",
            price=Decimal("50.00"),
            is_active=True,
        )
        data = {
            "action": "deactivate",
            "section": "catalog",
            "catalog_item_id": item.pk,
        }
        response = self.client.post(self.list_url, data)
        self.assertRedirects(response, f"{self.list_url}?section=catalog&view=list")
        item.refresh_from_db()
        self.assertFalse(item.is_active)

    def test_catalog_activate(self):
        item = CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Activar",
            price=Decimal("50.00"),
            is_active=False,
        )
        data = {
            "action": "activate",
            "section": "catalog",
            "catalog_item_id": item.pk,
        }
        response = self.client.post(self.list_url, data)
        self.assertRedirects(response, f"{self.list_url}?section=catalog&view=list")
        item.refresh_from_db()
        self.assertTrue(item.is_active)

    def test_catalog_deactivate_404(self):
        data = {
            "action": "deactivate",
            "section": "catalog",
            "catalog_item_id": 999,
        }
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, 404)

    def test_catalog_activate_404(self):
        data = {
            "action": "activate",
            "section": "catalog",
            "catalog_item_id": 999,
        }
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, 404)

    # --- Product commission zeroed ---
    def test_catalog_create_product_commission_zeroed(self):
        data = {
            "section": "catalog",
            "name": "Pomada",
            "kind": CatalogItem.Kind.PRODUCT,
            "price": "100.00",
            "barber_commission_percent": "50.00",
        }
        response = self.client.post(self.list_url, data)
        self.assertRedirects(response, f"{self.list_url}?section=catalog")
        item = CatalogItem.objects.get(name="Pomada")
        self.assertEqual(item.barber_commission_percent, Decimal("0.00"))

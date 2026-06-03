from decimal import Decimal
from urllib.parse import quote

from django.test import TestCase
from django.urls import reverse

from barberia.accounts.models import User
from barberia.catalog.models import CatalogItem


class CatalogViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="admin",
            password="pass1234",
            role=User.Role.ADMIN,
        )
        self.client.login(username="admin", password="pass1234")
        self.base_url = reverse("dashboard:home")

    def _list_url(self):
        return self.base_url + "?section=catalog&view=list"

    def _form_url(self):
        return self.base_url + "?section=catalog&view=form"

    def _edit_url(self, pk):
        return self.base_url + f"?section=catalog&view=edit&catalog_item={pk}"

    # --- Authentication ---
    def test_redirect_if_not_logged_in(self):
        self.client.logout()
        response = self.client.get(self._list_url())
        expected = f"{reverse('login')}?next={quote(self._list_url())}"
        self.assertRedirects(response, expected, fetch_redirect_response=False)

    # --- List ---
    def _catalog(self, count: int):
        for i in range(count):
            CatalogItem.objects.create(
                kind=(
                    CatalogItem.Kind.SERVICE if i % 2 == 0 else CatalogItem.Kind.PRODUCT
                ),
                name=f"Item {i}",
                price=Decimal(f"{i + 10}.00"),
                sku=f"ITM{i:04d}",
            )

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
        response = self.client.get(self._list_url())
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/home.html")
        self.assertContains(response, "Corte")
        self.assertContains(response, "Gel")

    # --- Pagination ---

    def test_catalog_pagination_page_2_shows_remaining(self):
        self._catalog(12)
        response = self.client.get(self.base_url + "?section=catalog&page=2")
        self.assertEqual(response.status_code, 200)
        items = response.context["catalog_items"]
        self.assertEqual(len(list(items.object_list)), 2)

    def test_catalog_pagination_no_duplicates_across_pages(self):
        self._catalog(14)
        page1 = self.client.get(self.base_url + "?section=catalog&page=1")
        page2 = self.client.get(self.base_url + "?section=catalog&page=2")
        ids_p1 = {e.pk for e in page1.context["catalog_items"].object_list}
        ids_p2 = {e.pk for e in page2.context["catalog_items"].object_list}
        self.assertFalse(ids_p1 & ids_p2)

    # --- Create GET ---
    def test_catalog_form_get(self):
        response = self.client.get(self._form_url())
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
        response = self.client.post(self.base_url, data)
        self.assertRedirects(response, self._list_url())
        self.assertTrue(CatalogItem.objects.filter(name="Corte nuevo").exists())

    def test_catalog_create_post_invalid(self):
        data = {
            "section": "catalog",
            "name": "",
            "kind": "",
            "price": "",
        }
        response = self.client.post(self.base_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)

    # --- Edit GET ---
    def test_catalog_edit_get_loads_instance(self):
        item = CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Corte editable",
            price=Decimal("50.00"),
        )
        response = self.client.get(self._edit_url(item.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["catalog_item_to_edit"].pk, item.pk)

    def test_catalog_edit_get_404_for_nonexistent(self):
        response = self.client.get(self._edit_url(999))
        self.assertEqual(response.status_code, 404)

    # --- Edit POST ---
    def test_catalog_edit_post_success(self):
        item = CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Original",
            price=Decimal("50.00"),
        )
        data = {
            "section": "catalog",
            "action": "update",
            "catalog_item_id": str(item.pk),
            "name": "Actualizado",
            "kind": CatalogItem.Kind.SERVICE,
            "price": "75.00",
            "barber_commission_percent": "20.00",
            "description": "",
        }
        response = self.client.post(self.base_url, data)
        self.assertRedirects(response, self._list_url())
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
            "section": "catalog",
            "action": "update",
            "catalog_item_id": str(item.pk),
            "name": "",
            "kind": "",
            "price": "",
        }
        response = self.client.post(self.base_url, data)
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
            "section": "catalog",
            "action": "deactivate",
            "catalog_item_id": str(item.pk),
        }
        response = self.client.post(self.base_url, data)
        self.assertRedirects(response, self._list_url())
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
            "section": "catalog",
            "action": "activate",
            "catalog_item_id": str(item.pk),
        }
        response = self.client.post(self.base_url, data)
        self.assertRedirects(response, self._list_url())
        item.refresh_from_db()
        self.assertTrue(item.is_active)

    def test_catalog_deactivate_404(self):
        data = {
            "section": "catalog",
            "action": "deactivate",
            "catalog_item_id": "999",
        }
        response = self.client.post(self.base_url, data)
        self.assertEqual(response.status_code, 404)

    def test_catalog_activate_404(self):
        data = {
            "section": "catalog",
            "action": "activate",
            "catalog_item_id": "999",
        }
        response = self.client.post(self.base_url, data)
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
        response = self.client.post(self.base_url, data)
        self.assertRedirects(response, self._list_url())
        item = CatalogItem.objects.get(name="Pomada")
        self.assertEqual(item.barber_commission_percent, Decimal("0.00"))

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from barberia.accounts.models import User
from barberia.catalog.models import CatalogItem
from barberia.common.tests.pagination_mixin import PaginationTestMixin
from barberia.dashboard.models import RoleCrudPermission, RoleMenuPermission
from barberia.routers import set_current_db_name


class CatalogFullLifecycleTest(TestCase):
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
        return f"{self.url}?section=catalog&view=list"

    # --- Service full lifecycle: create -> edit -> deactivate -> activate ---

    def test_service_full_lifecycle(self):
        create_data = {
            "section": "catalog",
            "name": "Corte Premium",
            "kind": CatalogItem.Kind.SERVICE,
            "price": "80.00",
            "barber_commission_percent": "30.00",
            "duration_minutes": "45",
            "description": "Corte de cabello premium",
            "is_active": True,
        }
        response = self.client.post(self.url, create_data)
        self.assertRedirects(response, self._list_url())
        service = CatalogItem.objects.get(name="Corte Premium")
        self.assertEqual(service.kind, CatalogItem.Kind.SERVICE)
        self.assertEqual(service.price, Decimal("80.00"))
        self.assertEqual(service.barber_commission_percent, Decimal("30.00"))
        self.assertEqual(service.duration_minutes, 45)
        self.assertTrue(service.is_active)

        edit_data = {
            "section": "catalog",
            "action": "update",
            "catalog_item_id": str(service.pk),
            "name": "Corte Premium Plus",
            "kind": CatalogItem.Kind.SERVICE,
            "price": "100.00",
            "barber_commission_percent": "35.00",
            "duration_minutes": "60",
            "description": "Corte premium plus",
        }
        response = self.client.post(self.url, edit_data)
        self.assertRedirects(response, self._list_url())
        service.refresh_from_db()
        self.assertEqual(service.name, "Corte Premium Plus")
        self.assertEqual(service.price, Decimal("100.00"))
        self.assertEqual(service.barber_commission_percent, Decimal("35.00"))

        deactivate_data = {
            "section": "catalog",
            "action": "deactivate",
            "catalog_item_id": str(service.pk),
        }
        response = self.client.post(self.url, deactivate_data)
        self.assertRedirects(response, self._list_url())
        service.refresh_from_db()
        self.assertFalse(service.is_active)

        activate_data = {
            "section": "catalog",
            "action": "activate",
            "catalog_item_id": str(service.pk),
        }
        response = self.client.post(self.url, activate_data)
        self.assertRedirects(response, self._list_url())
        service.refresh_from_db()
        self.assertTrue(service.is_active)

    # --- Product full lifecycle: create -> edit -> deactivate -> activate ---

    def test_product_full_lifecycle(self):
        create_data = {
            "section": "catalog",
            "name": "Shampoo Profesional",
            "kind": CatalogItem.Kind.PRODUCT,
            "price": "45.00",
            "barber_commission_percent": "50.00",
            "current_stock": "10",
            "description": "Shampoo para uso profesional",
            "is_active": True,
        }
        response = self.client.post(self.url, create_data)
        self.assertRedirects(response, self._list_url())
        product = CatalogItem.objects.get(name="Shampoo Profesional")
        self.assertEqual(product.kind, CatalogItem.Kind.PRODUCT)
        self.assertEqual(product.price, Decimal("45.00"))
        self.assertEqual(product.barber_commission_percent, Decimal("0.00"))
        self.assertEqual(product.current_stock, 0)
        self.assertTrue(product.is_active)

        edit_data = {
            "section": "catalog",
            "action": "update",
            "catalog_item_id": str(product.pk),
            "name": "Shampoo Premium",
            "kind": CatalogItem.Kind.PRODUCT,
            "price": "55.00",
            "barber_commission_percent": "0.00",
            "description": "Shampoo premium",
        }
        response = self.client.post(self.url, edit_data)
        self.assertRedirects(response, self._list_url())
        product.refresh_from_db()
        self.assertEqual(product.name, "Shampoo Premium")
        self.assertEqual(product.price, Decimal("55.00"))

        deactivate_data = {
            "section": "catalog",
            "action": "deactivate",
            "catalog_item_id": str(product.pk),
        }
        response = self.client.post(self.url, deactivate_data)
        self.assertRedirects(response, self._list_url())
        product.refresh_from_db()
        self.assertFalse(product.is_active)

        activate_data = {
            "section": "catalog",
            "action": "activate",
            "catalog_item_id": str(product.pk),
        }
        response = self.client.post(self.url, activate_data)
        self.assertRedirects(response, self._list_url())
        product.refresh_from_db()
        self.assertTrue(product.is_active)

    # --- Commission zeroed for products ---

    def test_product_commission_forced_to_zero(self):
        data = {
            "section": "catalog",
            "name": "Gel Fijador",
            "kind": CatalogItem.Kind.PRODUCT,
            "price": "25.00",
            "barber_commission_percent": "80.00",
        }
        self.client.post(self.url, data)
        product = CatalogItem.objects.get(name="Gel Fijador")
        self.assertEqual(product.barber_commission_percent, Decimal("0.00"))

    # --- Invalid data ---

    def test_create_service_without_name_rejected(self):
        data = {
            "section": "catalog",
            "name": "",
            "kind": CatalogItem.Kind.SERVICE,
            "price": "50.00",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)

    def test_create_service_without_price_rejected(self):
        data = {
            "section": "catalog",
            "name": "Sin Precio",
            "kind": CatalogItem.Kind.SERVICE,
            "price": "",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)

    # --- Permission-based access ---

    def test_non_admin_blocked_from_catalog_without_menu_permission(self):
        self.client.logout()
        _ = User.objects.create_user(
            username="no_catalog",
            password="pass1234",
            role=User.Role.BARBERO,
        )
        RoleMenuPermission.objects.create(role=User.Role.BARBERO, menu_key="overview")
        self.client.login(username="no_catalog", password="pass1234")
        response = self.client.get(f"{self.url}?section=catalog")
        self.assertRedirects(response, f"{self.url}?section=overview")

    def test_non_admin_can_view_catalog_with_menu_permission(self):
        self.client.logout()
        _ = User.objects.create_user(
            username="view_catalog",
            password="pass1234",
            role=User.Role.BARBERO,
        )
        RoleMenuPermission.objects.create(role=User.Role.BARBERO, menu_key="catalog")
        self.client.login(username="view_catalog", password="pass1234")
        response = self.client.get(f"{self.url}?section=catalog")
        self.assertEqual(response.status_code, 200)

    def test_non_admin_cannot_create_catalog_item_without_crud_permission(self):
        self.client.logout()
        _ = User.objects.create_user(
            username="no_create_catalog",
            password="pass1234",
            role=User.Role.BARBERO,
        )
        RoleMenuPermission.objects.create(role=User.Role.BARBERO, menu_key="catalog")
        self.client.login(username="no_create_catalog", password="pass1234")
        data = {
            "section": "catalog",
            "name": "Should Not Create",
            "kind": CatalogItem.Kind.SERVICE,
            "price": "50.00",
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, f"{self.url}?section=catalog&view=list")

    def test_non_admin_can_create_with_crud_permission(self):
        self.client.logout()
        _ = User.objects.create_user(
            username="create_catalog",
            password="pass1234",
            role=User.Role.BARBERO,
        )
        RoleMenuPermission.objects.create(role=User.Role.BARBERO, menu_key="catalog")
        RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key=RoleCrudPermission.AppKey.PRODUCTOS,
            action=RoleCrudPermission.Action.REGISTRAR,
        )
        self.client.login(username="create_catalog", password="pass1234")
        data = {
            "section": "catalog",
            "name": "Permitted Service",
            "kind": CatalogItem.Kind.SERVICE,
            "price": "60.00",
            "barber_commission_percent": "15.00",
            "is_active": True,
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(CatalogItem.objects.filter(name="Permitted Service").exists())

    # --- Search and filter ---

    def test_catalog_search_by_name(self):
        CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Corte Especial",
            price=Decimal("70.00"),
        )
        CatalogItem.objects.create(
            kind=CatalogItem.Kind.PRODUCT,
            name="Cera para Cabello",
            price=Decimal("35.00"),
        )
        response = self.client.get(f"{self.url}?section=catalog&catalog_search=Corte")
        self.assertEqual(response.status_code, 200)
        items = list(response.context["catalog_items"].object_list)
        names = [i.name for i in items]
        self.assertIn("Corte Especial", names)
        self.assertNotIn("Cera para Cabello", names)

    def test_catalog_filter_by_kind_service(self):
        CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Solo Servicio",
            price=Decimal("50.00"),
        )
        CatalogItem.objects.create(
            kind=CatalogItem.Kind.PRODUCT,
            name="Solo Producto",
            price=Decimal("30.00"),
        )
        response = self.client.get(f"{self.url}?section=catalog&catalog_kind=service")
        self.assertEqual(response.status_code, 200)
        items = list(response.context["catalog_items"].object_list)
        for i in items:
            self.assertEqual(i.kind, CatalogItem.Kind.SERVICE)

    def test_catalog_filter_by_kind_product(self):
        CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Otro Servicio",
            price=Decimal("50.00"),
        )
        CatalogItem.objects.create(
            kind=CatalogItem.Kind.PRODUCT,
            name="Otro Producto",
            price=Decimal("30.00"),
        )
        response = self.client.get(f"{self.url}?section=catalog&catalog_kind=product")
        self.assertEqual(response.status_code, 200)
        items = list(response.context["catalog_items"].object_list)
        for i in items:
            self.assertEqual(i.kind, CatalogItem.Kind.PRODUCT)

    def test_catalog_search_no_results(self):
        response = self.client.get(
            f"{self.url}?section=catalog&catalog_search=NONEXISTENT"
        )
        self.assertEqual(response.status_code, 200)
        items = list(response.context["catalog_items"].object_list)
        self.assertEqual(len(items), 0)

    def test_catalog_stats(self):
        CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE, name="Srv1", price=Decimal("10.00")
        )
        CatalogItem.objects.create(
            kind=CatalogItem.Kind.PRODUCT, name="Prd1", price=Decimal("20.00")
        )
        CatalogItem.objects.create(
            kind=CatalogItem.Kind.PRODUCT,
            name="Prd2",
            price=Decimal("30.00"),
            is_active=False,
        )
        response = self.client.get(f"{self.url}?section=catalog")
        self.assertEqual(response.status_code, 200)
        stats = response.context["catalog_stats"]
        self.assertIn("total", stats)
        self.assertIn("active", stats)
        self.assertIn("sales", stats)
        self.assertIn("products", stats)


class CatalogSearchFilterTest(TestCase):
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
        CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Corte Premium",
            price=Decimal("80.00"),
        )
        CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Corte Basico",
            price=Decimal("40.00"),
        )
        CatalogItem.objects.create(
            kind=CatalogItem.Kind.PRODUCT,
            name="Shampoo",
            price=Decimal("25.00"),
        )

    def tearDown(self):
        set_current_db_name(None)

    def test_search_by_name(self):
        response = self.client.get(f"{self.url}?section=catalog&catalog_search=Premium")
        self.assertEqual(response.status_code, 200)
        items = list(response.context["catalog_items"].object_list)
        names = [i.name for i in items]
        self.assertIn("Corte Premium", names)
        self.assertNotIn("Shampoo", names)

    def test_filter_by_kind_service(self):
        response = self.client.get(f"{self.url}?section=catalog&catalog_kind=service")
        self.assertEqual(response.status_code, 200)
        items = list(response.context["catalog_items"].object_list)
        for i in items:
            self.assertEqual(i.kind, CatalogItem.Kind.SERVICE)

    def test_filter_by_kind_product(self):
        response = self.client.get(f"{self.url}?section=catalog&catalog_kind=product")
        self.assertEqual(response.status_code, 200)
        items = list(response.context["catalog_items"].object_list)
        for i in items:
            self.assertEqual(i.kind, CatalogItem.Kind.PRODUCT)

    def test_search_no_results_shows_empty(self):
        response = self.client.get(
            f"{self.url}?section=catalog&catalog_search=XXXXXXXXX"
        )
        self.assertEqual(response.status_code, 200)
        items = list(response.context["catalog_items"].object_list)
        self.assertEqual(len(items), 0)

    def test_catalog_stats(self):
        response = self.client.get(f"{self.url}?section=catalog")
        self.assertEqual(response.status_code, 200)
        stats = response.context["catalog_stats"]
        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["sales"], 2)
        self.assertEqual(stats["products"], 1)


class CatalogPaginationTest(PaginationTestMixin, TestCase):
    section_name = "catalog"
    context_key = "catalog_items"

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
            CatalogItem.objects.create(
                kind=CatalogItem.Kind.SERVICE,
                name=f"Pagination Service {i}",
                price=Decimal(f"{(i % 50) + 10}.00"),
                is_active=True,
            )

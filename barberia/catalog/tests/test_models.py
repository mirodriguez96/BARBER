from decimal import Decimal

from django.test import TestCase

from barberia.catalog.models import CatalogItem


class CatalogItemModelTest(TestCase):
    def test_create_service_item(self):
        item = CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Corte de cabello",
            price=Decimal("50.00"),
            barber_commission_percent=Decimal("30.00"),
        )
        self.assertEqual(item.kind, CatalogItem.Kind.SERVICE)
        self.assertEqual(item.price, Decimal("50.00"))
        self.assertEqual(item.barber_commission_percent, Decimal("30.00"))

    def test_create_product_item(self):
        item = CatalogItem.objects.create(
            kind=CatalogItem.Kind.PRODUCT,
            name="Shampoo",
            price=Decimal("120.00"),
        )
        self.assertEqual(item.kind, CatalogItem.Kind.PRODUCT)

    def test_str_returns_name(self):
        item = CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Corte de cabello",
            price=Decimal("50.00"),
        )
        self.assertEqual(str(item), "Corte de cabello")

    def test_is_active_default_true(self):
        item = CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Corte",
            price=Decimal("50.00"),
        )
        self.assertTrue(item.is_active)

    def test_commission_default_zero(self):
        item = CatalogItem.objects.create(
            kind=CatalogItem.Kind.PRODUCT,
            name="Gel",
            price=Decimal("80.00"),
        )
        self.assertEqual(item.barber_commission_percent, Decimal("0.00"))

    def test_description_sku_blank_by_default(self):
        item = CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Corte",
            price=Decimal("50.00"),
        )
        self.assertEqual(item.description, "")
        self.assertEqual(item.sku, "")

    def test_current_stock_default_zero(self):
        item = CatalogItem.objects.create(
            kind=CatalogItem.Kind.PRODUCT,
            name="Gel",
            price=Decimal("80.00"),
        )
        self.assertEqual(item.current_stock, 0)

    def test_current_stock_can_be_set(self):
        item = CatalogItem.objects.create(
            kind=CatalogItem.Kind.PRODUCT,
            name="Shampoo",
            price=Decimal("120.00"),
            current_stock=50,
        )
        self.assertEqual(item.current_stock, 50)

    def test_current_stock_can_be_negative(self):
        item = CatalogItem.objects.create(
            kind=CatalogItem.Kind.PRODUCT,
            name="Aceite",
            price=Decimal("90.00"),
            current_stock=-5,
        )
        self.assertEqual(item.current_stock, -5)

    def test_current_stock_updates_correctly(self):
        item = CatalogItem.objects.create(
            kind=CatalogItem.Kind.PRODUCT,
            name="Test",
            price=Decimal("10.00"),
            current_stock=10,
        )
        item.current_stock += 5
        item.save(update_fields=["current_stock"])
        item.refresh_from_db()
        self.assertEqual(item.current_stock, 15)

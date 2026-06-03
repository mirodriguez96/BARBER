from decimal import Decimal

from django.test import TestCase

from barberia.catalog.forms import CatalogItemEditForm, CatalogItemForm
from barberia.catalog.models import CatalogItem


class CatalogItemFormTest(TestCase):
    def test_valid_service_item_with_commission(self):
        data = {
            "sku": "SRV001",
            "name": "Corte degradado",
            "kind": CatalogItem.Kind.SERVICE,
            "price": "70.00",
            "barber_commission_percent": "30.00",
            "is_active": True,
            "description": "Corte moderno",
        }
        form = CatalogItemForm(data)
        self.assertTrue(form.is_valid(), msg=dict(form.errors))
        item = form.save()
        self.assertEqual(item.barber_commission_percent, Decimal("30.00"))

    def test_product_commission_zeroed_in_clean(self):
        data = {
            "sku": "PRD001",
            "name": "Pomada",
            "kind": CatalogItem.Kind.PRODUCT,
            "price": "150.00",
            "barber_commission_percent": "50.00",
            "is_active": True,
            "description": "Pomada para cabello",
        }
        form = CatalogItemForm(data)
        self.assertTrue(form.is_valid(), msg=dict(form.errors))
        item = form.save()
        self.assertEqual(item.barber_commission_percent, Decimal("0.00"))

    def test_missing_required_fields(self):
        form = CatalogItemForm({})
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)
        self.assertIn("kind", form.errors)
        self.assertIn("price", form.errors)

    def test_description_optional(self):
        data = {
            "name": "Corte simple",
            "kind": CatalogItem.Kind.SERVICE,
            "price": "50.00",
            "barber_commission_percent": "0.00",
        }
        form = CatalogItemForm(data)
        self.assertTrue(form.is_valid(), msg=dict(form.errors))

    def test_bootstrap_css_classes(self):
        form = CatalogItemForm()
        for field_name, field in form.fields.items():
            widget_cls = field.widget.attrs.get("class", "")
            self.assertTrue(widget_cls, msg=f"Field {field_name} has no CSS class")


class CatalogItemEditFormTest(TestCase):
    def setUp(self):
        self.item = CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Corte original",
            price=Decimal("60.00"),
            barber_commission_percent=Decimal("20.00"),
        )

    def test_valid_edit_service(self):
        data = {
            "name": "Corte editado",
            "kind": CatalogItem.Kind.SERVICE,
            "price": "75.00",
            "barber_commission_percent": "25.00",
            "description": "Editado",
        }
        form = CatalogItemEditForm(data, instance=self.item)
        self.assertTrue(form.is_valid(), msg=dict(form.errors))
        form.save()
        self.item.refresh_from_db()
        self.assertEqual(self.item.name, "Corte editado")
        self.assertEqual(self.item.price, Decimal("75.00"))

    def test_product_commission_zeroed_in_clean(self):
        data = {
            "name": "Producto editado",
            "kind": CatalogItem.Kind.PRODUCT,
            "price": "100.00",
            "barber_commission_percent": "30.00",
            "description": "",
        }
        form = CatalogItemEditForm(data, instance=self.item)
        self.assertTrue(form.is_valid(), msg=dict(form.errors))
        item = form.save()
        self.assertEqual(item.barber_commission_percent, Decimal("0.00"))

    def test_missing_required_fields(self):
        form = CatalogItemEditForm({}, instance=self.item)
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)
        self.assertIn("kind", form.errors)

    def test_sku_absent_and_is_active_not_in_fields(self):
        form = CatalogItemEditForm(instance=self.item)
        self.assertNotIn("sku", form.fields)
        self.assertNotIn("is_active", form.fields)

    def test_bootstrap_css_classes(self):
        form = CatalogItemEditForm(instance=self.item)
        for field_name, field in form.fields.items():
            widget_cls = field.widget.attrs.get("class", "")
            self.assertTrue(widget_cls, msg=f"Field {field_name} has no CSS class")

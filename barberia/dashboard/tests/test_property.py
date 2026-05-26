from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.extra.django import TestCase

from barberia.catalog.models import CatalogItem
from barberia.dashboard.forms import CatalogItemEditForm, CatalogItemForm


class CatalogCommissionPropertyTest(TestCase):
    """Property-based tests for the commission-zeroing invariant."""

    def setUp(self):
        self.service = CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Base Service",
            price=Decimal("100.00"),
            barber_commission_percent=Decimal("20.00"),
        )
        self.product = CatalogItem.objects.create(
            kind=CatalogItem.Kind.PRODUCT,
            name="Base Product",
            price=Decimal("50.00"),
            barber_commission_percent=Decimal("0.00"),
        )

    @given(
        commission=st.integers(min_value=0, max_value=100),
    )
    @settings(max_examples=50)
    def test_catalog_item_form_product_zeroes_commission(self, commission):
        data = {
            "kind": CatalogItem.Kind.PRODUCT,
            "name": "Prop Test Product",
            "price": "100.00",
            "barber_commission_percent": str(commission),
        }
        form = CatalogItemForm(data=data)
        self.assertTrue(form.is_valid(), msg=form.errors)
        self.assertEqual(
            form.cleaned_data["barber_commission_percent"],
            Decimal("0.00"),
        )

    @given(
        commission=st.integers(min_value=0, max_value=100),
    )
    @settings(max_examples=50)
    def test_catalog_edit_form_product_zeroes_commission(self, commission):
        data = {
            "kind": CatalogItem.Kind.PRODUCT,
            "name": "Prop Edit Product",
            "price": "100.00",
            "barber_commission_percent": str(commission),
        }
        form = CatalogItemEditForm(data=data)
        self.assertTrue(form.is_valid(), msg=form.errors)
        self.assertEqual(
            form.cleaned_data["barber_commission_percent"],
            Decimal("0.00"),
        )

    @given(
        commission=st.integers(min_value=0, max_value=100),
    )
    @settings(max_examples=50)
    def test_catalog_item_form_service_preserves_commission(self, commission):
        data = {
            "kind": CatalogItem.Kind.SERVICE,
            "name": "Prop Test Service",
            "price": "200.00",
            "barber_commission_percent": str(commission),
        }
        form = CatalogItemForm(data=data)
        self.assertTrue(form.is_valid(), msg=form.errors)
        self.assertEqual(
            form.cleaned_data["barber_commission_percent"],
            Decimal(str(commission)),
        )

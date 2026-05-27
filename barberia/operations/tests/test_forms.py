from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from barberia.accounts.models import User
from barberia.catalog.models import CatalogItem
from barberia.dashboard.forms import SaleEditForm, SaleForm
from barberia.operations.models import Sale
from barberia.people.models import Client, Employee


class SaleFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="barber_admin",
            password="pass1234",
            role=User.Role.ADMIN,
        )
        self.employee = Employee.objects.create(
            user=self.user,
            full_name="Barber Test",
            document_id="DOC001",
            phone="123456789",
            is_active=True,
        )
        self.client = Client.objects.create(
            full_name="Client Test",
            phone="987654321",
        )
        self.service = CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Corte de cabello",
            price=Decimal("50.00"),
            barber_commission_percent=Decimal("20.00"),
            is_active=True,
            sku="SRV050",
        )
        self.inactive_service = CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Corte inactivo",
            price=Decimal("30.00"),
            is_active=False,
            sku="SRV030",
        )

    def test_barber_queryset_scoped_to_user_employee(self):
        form = SaleForm(user=self.user)
        self.assertIn(self.employee, form.fields["employee"].queryset)

    def test_barber_queryset_shows_all_for_user_without_employee(self):
        other_user = User.objects.create_user(
            username="other",
            password="pass1234",
            role=User.Role.ADMIN,
        )
        form = SaleForm(user=other_user)
        self.assertIn(self.employee, form.fields["employee"].queryset)

    def test_service_queryset_filters_active_only(self):
        form = SaleForm(user=self.user)
        self.assertIn(self.service, form.fields["product"].queryset)
        self.assertNotIn(self.inactive_service, form.fields["product"].queryset)

    def test_client_optional(self):
        form = SaleForm(user=self.user)
        self.assertFalse(form.fields["client"].required)

    def test_service_price_and_commission_readonly(self):
        form = SaleForm(user=self.user)
        self.assertIn("readonly", form.fields["product_price"].widget.attrs)
        self.assertIn("readonly", form.fields["commission_amount"].widget.attrs)

    def test_scheduled_for_initial_set(self):
        form = SaleForm(user=self.user)
        self.assertIsNotNone(form.fields["scheduled_for"].initial)

    def test_valid_form_creation(self):
        data = {
            "employee": self.employee.pk,
            "client": self.client.pk,
            "scheduled_for": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
            "product": self.service.pk,
            "product_price": "50.00",
            "commission_amount": "10.00",
            "tip_amount": "5.00",
            "notes": "Nota de prueba",
        }
        form = SaleForm(data, user=self.user)
        self.assertTrue(form.is_valid(), msg=dict(form.errors))

    def test_bootstrap_css_classes(self):
        form = SaleForm()
        for field_name, field in form.fields.items():
            widget_cls = field.widget.attrs.get("class", "")
            self.assertTrue(widget_cls, msg=f"Field {field_name} has no CSS class")


class SaleEditFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="barber_admin2",
            password="pass1234",
            role=User.Role.ADMIN,
        )
        self.employee = Employee.objects.create(
            user=self.user,
            full_name="Barber Edit",
            document_id="DOC002",
            phone="123456789",
            is_active=True,
        )
        self.service = CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Corte edit",
            price=Decimal("60.00"),
            barber_commission_percent=Decimal("25.00"),
            is_active=True,
            sku="SRV060",
        )
        self.record = Sale.objects.create(
            employee=self.employee,
            product=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("60.00"),
            commission_amount=Decimal("15.00"),
        )

    def test_valid_edit(self):
        data = {
            "employee": self.employee.pk,
            "product": self.service.pk,
            "product_price": "70.00",
            "commission_amount": "17.50",
            "tip_amount": "10.00",
        }
        form = SaleEditForm(data, instance=self.record, user=self.user)
        self.assertTrue(form.is_valid(), msg=dict(form.errors))
        form.save()
        self.record.refresh_from_db()
        self.assertEqual(self.record.tip_amount, Decimal("10.00"))

    def test_client_scheduled_for_and_notes_not_in_fields(self):
        form = SaleEditForm(instance=self.record)
        self.assertNotIn("client", form.fields)
        self.assertNotIn("scheduled_for", form.fields)
        self.assertNotIn("notes", form.fields)
        self.assertNotIn("status", form.fields)

    def test_barber_queryset_scoped(self):
        form = SaleEditForm(instance=self.record, user=self.user)
        self.assertIn(self.employee, form.fields["employee"].queryset)

    def test_service_queryset_filters_active_only(self):
        form = SaleEditForm(instance=self.record, user=self.user)
        self.assertIn(self.service, form.fields["product"].queryset)

    def test_service_price_and_commission_readonly(self):
        form = SaleEditForm(instance=self.record, user=self.user)
        self.assertIn("readonly", form.fields["product_price"].widget.attrs)
        self.assertIn("readonly", form.fields["commission_amount"].widget.attrs)

    def test_missing_required_fields(self):
        form = SaleEditForm({}, instance=self.record, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("employee", form.errors)

    def test_bootstrap_css_classes(self):
        form = SaleEditForm(instance=self.record)
        for field_name, field in form.fields.items():
            widget_cls = field.widget.attrs.get("class", "")
            self.assertTrue(widget_cls, msg=f"Field {field_name} has no CSS class")

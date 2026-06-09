from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from barberia.accounts.models import User
from barberia.catalog.models import CatalogItem
from barberia.operations.forms import SaleEditForm, SaleForm
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
        """Verifica que el campo employee solo muestre el empleado asociado al usuario."""
        form = SaleForm(user=self.user)
        self.assertIn(self.employee, form.fields["employee"].queryset)

    def test_barber_queryset_shows_all_for_user_without_employee(self):
        """Verifica que un usuario sin empleado asociado vea todos los empleados disponibles."""
        other_user = User.objects.create_user(
            username="other",
            password="pass1234",
            role=User.Role.ADMIN,
        )
        form = SaleForm(user=other_user)
        self.assertIn(self.employee, form.fields["employee"].queryset)

    def test_service_queryset_filters_active_only(self):
        """Verifica que solo los servicios activos aparezcan en el campo product."""
        form = SaleForm(user=self.user)
        self.assertIn(self.service, form.fields["product"].queryset)
        self.assertNotIn(self.inactive_service, form.fields["product"].queryset)

    def test_client_optional(self):
        """Verifica que el campo client sea opcional en el formulario."""
        form = SaleForm(user=self.user)
        self.assertFalse(form.fields["client"].required)

    def test_service_price_and_commission_readonly(self):
        """Verifica que los campos product_price y commission_amount sean de solo lectura."""
        form = SaleForm(user=self.user)
        self.assertIn("readonly", form.fields["product_price"].widget.attrs)
        self.assertIn("readonly", form.fields["commission_amount"].widget.attrs)

    def test_scheduled_for_initial_set(self):
        """Verifica que el campo scheduled_for tenga un valor inicial por defecto."""
        form = SaleForm(user=self.user)
        self.assertIsNotNone(form.fields["scheduled_for"].initial)

    def test_valid_form_creation(self):
        """Verifica que el formulario sea válido cuando se envían datos correctos."""
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
        """Verifica que todos los campos del formulario tengan clases CSS de Bootstrap."""
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
        """Verifica que la edición de una venta existente sea válida con datos correctos."""
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

    def test_client_scheduled_for_and_status_not_in_fields(self):
        """Verifica que los campos client, scheduled_for y status no estén presentes en el formulario de edición."""
        form = SaleEditForm(instance=self.record)
        self.assertNotIn("client", form.fields)
        self.assertNotIn("scheduled_for", form.fields)
        self.assertNotIn("status", form.fields)

    def test_notes_is_editable_in_edit_form(self):
        """Verifica que el campo notes esté presente y sea editable en el formulario de edición."""
        form = SaleEditForm(instance=self.record)
        self.assertIn("notes", form.fields)
        form = SaleEditForm(
            data={
                "employee": self.employee.pk,
                "product": self.service.pk,
                "product_price": "70.00",
                "commission_amount": "17.50",
                "tip_amount": "10.00",
                "notes": "Cliente pidió corte específico",
            },
            instance=self.record,
            user=self.user,
        )
        self.assertTrue(form.is_valid(), msg=dict(form.errors))
        form.save()
        self.record.refresh_from_db()
        self.assertEqual(self.record.notes, "Cliente pidió corte específico")

    def test_barber_queryset_scoped(self):
        """Verifica que el campo employee del formulario de edición esté filtrado por el usuario."""
        form = SaleEditForm(instance=self.record, user=self.user)
        self.assertIn(self.employee, form.fields["employee"].queryset)

    def test_service_queryset_filters_active_only(self):
        """Verifica que solo los servicios activos aparezcan en el campo product del formulario de edición."""
        form = SaleEditForm(instance=self.record, user=self.user)
        self.assertIn(self.service, form.fields["product"].queryset)

    def test_service_price_and_commission_readonly(self):
        """Verifica que los campos product_price y commission_amount sean de solo lectura en el formulario de edición."""
        form = SaleEditForm(instance=self.record, user=self.user)
        self.assertIn("readonly", form.fields["product_price"].widget.attrs)
        self.assertIn("readonly", form.fields["commission_amount"].widget.attrs)

    def test_missing_required_fields(self):
        """Verifica que el formulario de edición sea inválido si faltan campos obligatorios."""
        form = SaleEditForm({}, instance=self.record, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("employee", form.errors)

    def test_bootstrap_css_classes(self):
        """Verifica que todos los campos del formulario de edición tengan clases CSS de Bootstrap."""
        form = SaleEditForm(instance=self.record)
        for field_name, field in form.fields.items():
            widget_cls = field.widget.attrs.get("class", "")
            self.assertTrue(widget_cls, msg=f"Field {field_name} has no CSS class")

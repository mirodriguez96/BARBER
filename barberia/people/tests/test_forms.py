from django.test import TestCase
from django.contrib.auth import get_user_model

from barberia.people.models import Employee
from barberia.dashboard.forms import BarberForm, BarberEditForm

User = get_user_model()


class BarberFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="barbero1",
            password="testpass123",
            role=User.Role.BARBERO,
        )
        self.available_user = User.objects.create_user(
            username="barbero2",
            password="testpass123",
        )
        self.valid_data = {
            "user": self.available_user.pk,
            "full_name": "Juan Pérez",
            "document_id": "1020304050",
            "phone": "3001234567",
            "email": "juan@example.com",
        }

    def test_valid_form_creates_employee(self):
        form = BarberForm(data=self.valid_data)
        self.assertTrue(form.is_valid())
        employee = form.save()
        self.assertEqual(Employee.objects.count(), 1)
        self.assertEqual(employee.full_name, "Juan Pérez")
        self.assertEqual(employee.document_id, "1020304050")

    def test_duplicate_document_id_rejected(self):
        Employee.objects.create(
            user=self.user,
            full_name="Barbero Existente",
            document_id="1020304050",
            phone="3001234567",
        )
        form = BarberForm(data=self.valid_data)
        self.assertFalse(form.is_valid())
        self.assertIn("document_id", form.errors)

    def test_empty_phone_rejected(self):
        data = self.valid_data.copy()
        data["phone"] = ""
        form = BarberForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("phone", form.errors)

    def test_blank_phone_rejected_by_clean(self):
        data = self.valid_data.copy()
        data["phone"] = "   "
        form = BarberForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("phone", form.errors)
        self.assertIn(
            "obligatorio",
            "".join(form.errors["phone"]).lower(),
        )

    def test_missing_user_rejected(self):
        data = self.valid_data.copy()
        del data["user"]
        form = BarberForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("user", form.errors)

    def test_user_queryset_excludes_employed_users(self):
        Employee.objects.create(
            user=self.user,
            full_name="Barbero Existente",
            document_id="1020304050",
            phone="3001234567",
        )
        form = BarberForm()
        self.assertNotIn(self.user, form.fields["user"].queryset)
        self.assertIn(self.available_user, form.fields["user"].queryset)

    def test_edit_form_includes_current_user(self):
        employee = Employee.objects.create(
            user=self.user,
            full_name="Barbero Edit",
            document_id="9988776655",
            phone="3001234567",
        )
        form = BarberForm(instance=employee)
        self.assertIn(self.user, form.fields["user"].queryset)

    def test_email_optional(self):
        data = self.valid_data.copy()
        data["email"] = ""
        form = BarberForm(data=data)
        self.assertTrue(form.is_valid())


class BarberEditFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="barbero1",
            password="testpass123",
        )
        self.employee = Employee.objects.create(
            user=self.user,
            full_name="Juan Pérez",
            document_id="1020304050",
            phone="3001234567",
        )
        self.valid_data = {
            "full_name": "Juan Actualizado",
            "phone": "3111111111",
            "email": "nuevo@email.com",
        }

    def test_valid_edit_form_updates_employee(self):
        form = BarberEditForm(
            data=self.valid_data,
            instance=self.employee,
        )
        self.assertTrue(
            form.is_valid(),
            msg=f"Form errors: {form.errors}",
        )
        form.save()
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.full_name, "Juan Actualizado")
        self.assertEqual(self.employee.phone, "3111111111")
        self.assertEqual(self.employee.email, "nuevo@email.com")

    def test_empty_phone_rejected_on_edit(self):
        form = BarberEditForm(
            data={"full_name": "Juan Pérez", "phone": ""},
            instance=self.employee,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("phone", form.errors)

    def test_blank_phone_rejected_by_clean_on_edit(self):
        form = BarberEditForm(
            data={"full_name": "Juan Pérez", "phone": "   "},
            instance=self.employee,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("phone", form.errors)
        self.assertIn(
            "obligatorio",
            "".join(form.errors["phone"]).lower(),
        )

    def test_email_optional_on_edit(self):
        form = BarberEditForm(
            data={"full_name": "Juan Pérez", "phone": "3001234567", "email": ""},
            instance=self.employee,
        )
        self.assertTrue(form.is_valid())

    def test_full_name_required(self):
        form = BarberEditForm(
            data={"full_name": "", "phone": "3001234567"},
            instance=self.employee,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("full_name", form.errors)

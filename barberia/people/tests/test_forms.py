from django.contrib.auth import get_user_model
from django.test import TestCase

from barberia.dashboard.forms import (
    BarberEditForm,
    BarberForm,
    ClientEditForm,
    ClientForm,
)
from barberia.people.models import Client, Employee

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
            "role": User.Role.BARBERO,
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
            full_name="Colaborador Existente",
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
            full_name="Colaborador Existente",
            document_id="1020304050",
            phone="3001234567",
        )
        form = BarberForm()
        self.assertNotIn(self.user, form.fields["user"].queryset)
        self.assertIn(self.available_user, form.fields["user"].queryset)

    def test_edit_form_includes_current_user(self):
        employee = Employee.objects.create(
            user=self.user,
            full_name="Colaborador Edit",
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
            "role": User.Role.BARBERO,
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
            data={
                "full_name": "Juan Pérez",
                "phone": "3001234567",
                "email": "",
                "role": User.Role.BARBERO,
            },
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


class ClientFormTest(TestCase):
    def setUp(self):
        self.valid_data = {
            "full_name": "María García",
            "document_id": "1020304050",
            "phone": "3101234567",
            "birth_date": "1995-06-15",
        }

    def test_valid_form_creates_client(self):
        form = ClientForm(data=self.valid_data)
        self.assertTrue(form.is_valid())
        client = form.save()
        self.assertEqual(Client.objects.count(), 1)
        self.assertEqual(client.full_name, "María García")
        self.assertEqual(client.document_id, "1020304050")

    def test_birth_date_optional(self):
        data = self.valid_data.copy()
        del data["birth_date"]
        form = ClientForm(data=data)
        self.assertTrue(form.is_valid())

    def test_duplicate_document_id_rejected(self):
        Client.objects.create(
            full_name="Existente",
            document_id="1020304050",
            phone="3001111111",
        )
        form = ClientForm(data=self.valid_data)
        self.assertFalse(form.is_valid())
        self.assertIn("document_id", form.errors)

    def test_empty_phone_rejected(self):
        data = self.valid_data.copy()
        data["phone"] = ""
        form = ClientForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("phone", form.errors)

    def test_blank_phone_rejected_by_clean(self):
        data = self.valid_data.copy()
        data["phone"] = "   "
        form = ClientForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("phone", form.errors)
        self.assertIn(
            "obligatorio",
            "".join(form.errors["phone"]).lower(),
        )

    def test_empty_document_id_rejected(self):
        data = self.valid_data.copy()
        data["document_id"] = ""
        form = ClientForm(data=data)
        self.assertIn("document_id", form.errors)

    def test_missing_full_name_rejected(self):
        data = self.valid_data.copy()
        del data["full_name"]
        form = ClientForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("full_name", form.errors)


class ClientEditFormTest(TestCase):
    def setUp(self):
        self.client_model = Client.objects.create(
            full_name="María García",
            document_id="1020304050",
            phone="3101234567",
            birth_date="1995-06-15",
        )
        self.valid_data = {
            "full_name": "María Actualizada",
            "document_id": "1020304050",
            "phone": "3111111111",
            "birth_date": "1995-06-15",
        }

    def test_valid_edit_form_updates_client(self):
        form = ClientEditForm(
            data=self.valid_data,
            instance=self.client_model,
        )
        self.assertTrue(
            form.is_valid(),
            msg=f"Form errors: {form.errors}",
        )
        form.save()
        self.client_model.refresh_from_db()
        self.assertEqual(self.client_model.full_name, "María Actualizada")
        self.assertEqual(self.client_model.phone, "3111111111")

    def test_empty_phone_rejected_on_edit(self):
        form = ClientEditForm(
            data={"full_name": "María", "document_id": "1020304050", "phone": ""},
            instance=self.client_model,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("phone", form.errors)

    def test_blank_phone_rejected_by_clean_on_edit(self):
        form = ClientEditForm(
            data={"full_name": "María", "document_id": "1020304050", "phone": "   "},
            instance=self.client_model,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("phone", form.errors)
        self.assertIn(
            "obligatorio",
            "".join(form.errors["phone"]).lower(),
        )

    def test_duplicate_document_id_rejected_on_edit(self):
        Client.objects.create(
            full_name="Otro Cliente",
            document_id="9988776655",
            phone="3000000000",
        )
        form = ClientEditForm(
            data={
                "full_name": "María",
                "document_id": "9988776655",
                "phone": "3101234567",
            },
            instance=self.client_model,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("document_id", form.errors)

    def test_birth_date_optional_on_edit(self):
        form = ClientEditForm(
            data={
                "full_name": "María",
                "document_id": "1020304050",
                "phone": "3101234567",
            },
            instance=self.client_model,
        )
        self.assertTrue(form.is_valid())

    def test_full_name_required_on_edit(self):
        form = ClientEditForm(
            data={"full_name": "", "document_id": "1020304050", "phone": "3101234567"},
            instance=self.client_model,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("full_name", form.errors)

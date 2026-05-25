from django.test import TestCase
from barberia.accounts.forms import BarberUserCreationForm
from barberia.accounts.models import User


class BarberUserCreationFormTest(TestCase):
    def test_valid_form_creates_user(self):
        data = {
            "username": "newbarber",
            "first_name": "Carlos",
            "last_name": "Lopez",
            "email": "carlos@example.com",
            "phone": "123456789",
            "role": User.Role.BARBERO,
            "password1": "StrongP4ss!",
            "password2": "StrongP4ss!",
        }
        form = BarberUserCreationForm(data)
        self.assertTrue(form.is_valid(), msg=dict(form.errors))
        user = form.save()
        self.assertEqual(user.role, User.Role.BARBERO)
        self.assertEqual(user.first_name, "Carlos")

    def test_password_mismatch_invalid(self):
        data = {
            "username": "newbarber",
            "first_name": "Carlos",
            "last_name": "Lopez",
            "email": "carlos@example.com",
            "phone": "123456789",
            "role": User.Role.BARBERO,
            "password1": "StrongP4ss!",
            "password2": "MismatchP4ss!",
        }
        form = BarberUserCreationForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)

    def test_missing_required_fields(self):
        form = BarberUserCreationForm({})
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)
        self.assertIn("password1", form.errors)
        self.assertIn("password2", form.errors)

    def test_bootstrap_css_classes(self):
        form = BarberUserCreationForm()
        for field_name, field in form.fields.items():
            attrs = field.widget.attrs
            if field_name == "role":
                self.assertIn("form-select", attrs.get("class", ""))
            else:
                self.assertIn("form-control", attrs.get("class", ""))

    def test_placeholders_set(self):
        form = BarberUserCreationForm()
        for field_name, field in form.fields.items():
            if field_name == "role":
                continue
            self.assertIn("placeholder", field.widget.attrs)

    def test_username_unique_validation(self):
        User.objects.create_user(
            username="existing",
            password="pass1234",
            role=User.Role.ADMIN,
        )
        data = {
            "username": "existing",
            "first_name": "Otro",
            "last_name": "User",
            "password1": "StrongP4ss!",
            "password2": "StrongP4ss!",
        }
        form = BarberUserCreationForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_email_optional(self):
        data = {
            "username": "noemail",
            "first_name": "No",
            "last_name": "Email",
            "phone": "123456789",
            "role": User.Role.BARBERO,
            "password1": "StrongP4ss!",
            "password2": "StrongP4ss!",
        }
        form = BarberUserCreationForm(data)
        self.assertTrue(form.is_valid(), msg=dict(form.errors))

from django.test import TestCase
from django.urls import reverse
from barberia.accounts.models import User


class LoginViewTest(TestCase):
    def test_get_renders_login_template(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/login.html")

    def test_redirect_authenticated_user(self):
        User.objects.create_user(
            username="testuser",
            password="pass1234",
            role=User.Role.ADMIN,
        )
        self.client.login(username="testuser", password="pass1234")
        response = self.client.get(reverse("login"))
        self.assertRedirects(response, reverse("dashboard:home"))

    def test_post_valid_credentials(self):
        User.objects.create_user(
            username="testuser",
            password="pass1234",
            role=User.Role.ADMIN,
        )
        data = {
            "username": "testuser",
            "password": "pass1234",
        }
        response = self.client.post(reverse("login"), data)
        self.assertRedirects(response, reverse("dashboard:home"))

    def test_post_invalid_credentials(self):
        data = {
            "username": "nonexistent",
            "password": "wrong",
        }
        response = self.client.post(reverse("login"), data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        self.assertTrue(response.context["form"].errors)

    def test_root_url_also_renders_login(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/login.html")

    def test_form_has_bootstrap_classes(self):
        response = self.client.get(reverse("login"))
        form = response.context["form"]
        for field_name, field in form.fields.items():
            widget_cls = field.widget.attrs.get("class", "")
            self.assertIn("form-control", widget_cls)
            self.assertIn("placeholder", field.widget.attrs)

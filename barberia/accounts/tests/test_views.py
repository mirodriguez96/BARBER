from django.test import TestCase
from django.urls import reverse
from barberia.accounts.models import User

register_url = reverse("register")


class RegisterViewTest(TestCase):
    def test_get_renders_form(self):
        response = self.client.get(register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/register.html")

    def test_post_valid_creates_user_and_redirects(self):
        data = {
            "username": "newuser",
            "first_name": "Test",
            "last_name": "User",
            "email": "test@example.com",
            "phone": "123456789",
            "role": User.Role.BARBERO,
            "password1": "StrongP4ss!",
            "password2": "StrongP4ss!",
        }
        response = self.client.post(register_url, data)
        self.assertRedirects(response, reverse("dashboard:home"))
        self.assertTrue(User.objects.filter(username="newuser").exists())
        user = User.objects.get(username="newuser")
        self.assertTrue(user.is_staff)

    def test_post_valid_auto_logs_in(self):
        data = {
            "username": "autologin",
            "first_name": "Auto",
            "last_name": "Login",
            "phone": "123456789",
            "role": User.Role.BARBERO,
            "password1": "StrongP4ss!",
            "password2": "StrongP4ss!",
        }
        self.client.post(register_url, data)
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 200)

    def test_post_invalid_rerenders_form(self):
        data = {
            "username": "",
            "password1": "pass1234",
            "password2": "pass1234",
        }
        response = self.client.post(register_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/register.html")

    def test_post_password_mismatch_shows_errors(self):
        data = {
            "username": "badpass",
            "first_name": "Bad",
            "last_name": "Pass",
            "role": User.Role.BARBERO,
            "password1": "StrongP4ss!",
            "password2": "DifferentP4ss!",
        }
        response = self.client.post(register_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("password2", response.context["form"].errors)

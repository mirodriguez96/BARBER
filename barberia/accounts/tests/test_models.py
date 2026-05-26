from django.test import TestCase

from barberia.accounts.models import User


class UserModelTest(TestCase):
    def test_create_user_with_role(self):
        user = User.objects.create_user(
            username="testuser",
            password="pass1234",
            role=User.Role.BARBERO,
        )
        self.assertEqual(user.role, User.Role.BARBERO)
        self.assertTrue(user.check_password("pass1234"))

    def test_str_returns_full_name(self):
        user = User.objects.create_user(
            username="testuser",
            password="pass1234",
            first_name="Juan",
            last_name="Perez",
            role=User.Role.ADMIN,
        )
        self.assertEqual(str(user), "Juan Perez")

    def test_str_falls_back_to_username(self):
        user = User.objects.create_user(
            username="testuser",
            password="pass1234",
            role=User.Role.ADMIN,
        )
        self.assertEqual(str(user), "testuser")

    def test_phone_blank_by_default(self):
        user = User.objects.create_user(
            username="testuser",
            password="pass1234",
            role=User.Role.ADMIN,
        )
        self.assertEqual(user.phone, "")

    def test_role_choices_admin(self):
        user = User.objects.create_user(
            username="admin",
            password="pass1234",
            role=User.Role.ADMIN,
        )
        self.assertEqual(user.role, "admin")

    def test_role_choices_barbero(self):
        user = User.objects.create_user(
            username="colaborador",
            password="pass1234",
            role=User.Role.BARBERO,
        )
        self.assertEqual(user.role, "colaborador")

    def test_create_superuser(self):
        user = User.objects.create_superuser(
            username="super",
            password="pass1234",
        )
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    def test_default_role_is_admin(self):
        user = User.objects.create_user(
            username="testuser",
            password="pass1234",
        )
        self.assertEqual(user.role, User.Role.ADMIN)

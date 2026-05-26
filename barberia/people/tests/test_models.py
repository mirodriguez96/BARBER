from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from barberia.people.models import Client, Employee

User = get_user_model()


class EmployeeModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="barbero1",
            password="testpass123",
            role=User.Role.BARBERO,
        )
        self.employee = Employee.objects.create(
            user=self.user,
            full_name="Juan Pérez",
            document_id="1020304050",
            phone="3001234567",
            email="juan@example.com",
        )

    def test_create_employee(self):
        self.assertEqual(self.employee.full_name, "Juan Pérez")
        self.assertEqual(self.employee.document_id, "1020304050")
        self.assertEqual(self.employee.phone, "3001234567")
        self.assertEqual(self.employee.email, "juan@example.com")
        self.assertTrue(self.employee.is_active)
        self.assertEqual(Employee.objects.count(), 1)

    def test_employee_user_relation(self):
        self.assertEqual(self.employee.user, self.user)
        self.assertEqual(self.employee.user.username, "barbero1")
        self.assertTrue(hasattr(self.user, "employee"))

    def test_unique_document_id(self):
        with self.assertRaises(IntegrityError):
            Employee.objects.create(
                user=User.objects.create_user(
                    username="barbero2", password="testpass123",
                ),
                full_name="Otro Barbero",
                document_id="1020304050",
                phone="3111111111",
            )

    def test_timestamps(self):
        self.assertIsNotNone(self.employee.created_at)
        self.assertIsNotNone(self.employee.updated_at)

    def test_string_representation(self):
        self.assertEqual(str(self.employee), "Juan Pérez")

    def test_is_active_default_true(self):
        new_employee = Employee.objects.create(
            user=User.objects.create_user(username="barbero3", password="testpass123"),
            full_name="Nuevo Barbero",
            document_id="9988776655",
            phone="3222222222",
        )
        self.assertTrue(new_employee.is_active)


class ClientModelTest(TestCase):
    def setUp(self):
        self.client = Client.objects.create(
            full_name="María García",
            document_id="1020304050",
            phone="3101234567",
            birth_date="1995-06-15",
        )

    def test_create_client(self):
        self.assertEqual(self.client.full_name, "María García")
        self.assertEqual(self.client.document_id, "1020304050")
        self.assertEqual(self.client.phone, "3101234567")
        self.assertEqual(str(self.client.birth_date), "1995-06-15")
        self.assertTrue(self.client.is_active)
        self.assertEqual(Client.objects.count(), 1)

    def test_birth_date_optional(self):
        client = Client.objects.create(
            full_name="Sin Fecha",
            document_id="9988776655",
            phone="3111111111",
        )
        self.assertIsNone(client.birth_date)

    def test_unique_document_id(self):
        with self.assertRaises(IntegrityError):
            Client.objects.create(
                full_name="Otro Cliente",
                document_id="1020304050",
                phone="3222222222",
            )

    def test_string_representation(self):
        self.assertEqual(str(self.client), "María García")

    def test_client_timestamps(self):
        self.assertIsNotNone(self.client.created_at)
        self.assertIsNotNone(self.client.updated_at)

    def test_is_active_default_true(self):
        client = Client.objects.create(
            full_name="Cliente Nuevo",
            document_id="1122334455",
            phone="3000000000",
        )
        self.assertTrue(client.is_active)

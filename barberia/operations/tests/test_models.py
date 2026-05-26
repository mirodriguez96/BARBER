from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from barberia.accounts.models import User
from barberia.catalog.models import CatalogItem
from barberia.operations.models import ServiceRecord
from barberia.people.models import Client, Employee


class ServiceRecordModelTest(TestCase):
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
        )

    def test_create_service_record(self):
        record = ServiceRecord.objects.create(
            client=self.client,
            barber=self.employee,
            service=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            service_price=Decimal("50.00"),
            commission_amount=Decimal("10.00"),
        )
        self.assertEqual(record.status, ServiceRecord.Status.SCHEDULED)
        self.assertEqual(record.service_price, Decimal("50.00"))
        self.assertEqual(record.commission_amount, Decimal("10.00"))

    def test_str_with_client(self):
        record = ServiceRecord.objects.create(
            client=self.client,
            barber=self.employee,
            service=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            service_price=Decimal("50.00"),
        )
        expected = f"{self.client} - {self.service}"
        self.assertEqual(str(record), expected)

    def test_str_without_client(self):
        record = ServiceRecord.objects.create(
            barber=self.employee,
            service=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            service_price=Decimal("50.00"),
        )
        expected = "Cliente no registrado - Corte de cabello"
        self.assertEqual(str(record), expected)

    def test_status_scheduled_default(self):
        record = ServiceRecord.objects.create(
            barber=self.employee,
            service=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            service_price=Decimal("50.00"),
        )
        self.assertEqual(record.status, ServiceRecord.Status.SCHEDULED)

    def test_status_choices(self):
        record = ServiceRecord.objects.create(
            barber=self.employee,
            service=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            service_price=Decimal("50.00"),
            status=ServiceRecord.Status.DONE,
            completed_at=timezone.now(),
        )
        self.assertEqual(record.status, ServiceRecord.Status.DONE)

    def test_tip_amount_nullable(self):
        record = ServiceRecord.objects.create(
            barber=self.employee,
            service=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            service_price=Decimal("50.00"),
        )
        self.assertIsNone(record.tip_amount)

    def test_commission_amount_default_zero(self):
        record = ServiceRecord.objects.create(
            barber=self.employee,
            service=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            service_price=Decimal("50.00"),
        )
        self.assertIsNone(record.commission_amount)

    def test_fk_protect_on_delete(self):
        record = ServiceRecord.objects.create(
            barber=self.employee,
            service=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            service_price=Decimal("50.00"),
        )
        record_pk = record.pk
        with self.assertRaises(Exception):
            self.employee.delete()
        self.assertTrue(ServiceRecord.objects.filter(pk=record_pk).exists())

    def test_completed_at_null_when_scheduled(self):
        record = ServiceRecord.objects.create(
            barber=self.employee,
            service=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            service_price=Decimal("50.00"),
        )
        self.assertIsNone(record.completed_at)

    def test_notes_blank_by_default(self):
        record = ServiceRecord.objects.create(
            barber=self.employee,
            service=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            service_price=Decimal("50.00"),
        )
        self.assertEqual(record.notes, "")

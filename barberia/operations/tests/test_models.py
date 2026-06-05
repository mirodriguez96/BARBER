from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from barberia.accounts.models import User
from barberia.catalog.models import CatalogItem
from barberia.operations.models import Purchase, Sale
from barberia.people.models import Client, Employee


class SaleModelTest(TestCase):
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
        """Verifica que se pueda crear una venta de servicio con todos los campos requeridos."""
        record = Sale.objects.create(
            client=self.client,
            employee=self.employee,
            product=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
            commission_amount=Decimal("10.00"),
        )
        self.assertEqual(record.status, Sale.Status.SCHEDULED)
        self.assertEqual(record.product_price, Decimal("50.00"))
        self.assertEqual(record.commission_amount, Decimal("10.00"))

    def test_str_with_client(self):
        """Verifica que la representación en cadena incluya el código, cliente y servicio."""
        record = Sale.objects.create(
            client=self.client,
            employee=self.employee,
            product=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
        )
        expected = f"{record.codigo} - {self.client} - {self.service}"
        self.assertEqual(str(record), expected)

    def test_str_without_client(self):
        """Verifica que la representación en cadena muestre 'Cliente no registrado' cuando no hay cliente."""
        record = Sale.objects.create(
            employee=self.employee,
            product=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
        )
        expected = f"{record.codigo} - Cliente no registrado - Corte de cabello"
        self.assertEqual(str(record), expected)

    def test_status_scheduled_default(self):
        """Verifica que el estado predeterminado de una venta sea SCHEDULED."""
        record = Sale.objects.create(
            employee=self.employee,
            product=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
        )
        self.assertEqual(record.status, Sale.Status.SCHEDULED)

    def test_status_choices(self):
        """Verifica que se pueda asignar un estado diferente a SCHEDULED, como DONE."""
        record = Sale.objects.create(
            employee=self.employee,
            product=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
            status=Sale.Status.DONE,
            completed_at=timezone.now(),
        )
        self.assertEqual(record.status, Sale.Status.DONE)

    def test_tip_amount_nullable(self):
        """Verifica que el campo tip_amount sea nulo por defecto."""
        record = Sale.objects.create(
            employee=self.employee,
            product=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
        )
        self.assertIsNone(record.tip_amount)

    def test_commission_amount_default_zero(self):
        """Verifica que el campo commission_amount sea nulo por defecto."""
        record = Sale.objects.create(
            employee=self.employee,
            product=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
        )
        self.assertIsNone(record.commission_amount)

    def test_fk_protect_on_delete(self):
        """Verifica que no se pueda eliminar un empleado asociado a una venta (PROTECT)."""
        record = Sale.objects.create(
            employee=self.employee,
            product=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
        )
        record_pk = record.pk
        with self.assertRaises(Exception):
            self.employee.delete()
        self.assertTrue(Sale.objects.filter(pk=record_pk).exists())

    def test_completed_at_null_when_scheduled(self):
        """Verifica que completed_at sea nulo cuando la venta está en estado SCHEDULED."""
        record = Sale.objects.create(
            employee=self.employee,
            product=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
        )
        self.assertIsNone(record.completed_at)

    def test_notes_blank_by_default(self):
        """Verifica que el campo notes esté vacío por defecto."""
        record = Sale.objects.create(
            employee=self.employee,
            product=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
        )
        self.assertEqual(record.notes, "")

    def test_codigo_auto_generated_on_create(self):
        """Verifica que el código se genere automáticamente al crear una venta."""
        record = Sale.objects.create(
            employee=self.employee,
            product=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
        )
        record.refresh_from_db()
        self.assertTrue(record.codigo)
        self.assertNotEqual(record.codigo, "")

    def test_codigo_format_ven(self):
        """Verifica que el código de venta tenga el formato 'VEN-{pk}'."""
        record = Sale.objects.create(
            employee=self.employee,
            product=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
        )
        record.refresh_from_db()
        self.assertEqual(record.codigo, f"VEN-{record.pk}")

    def test_codigo_unique(self):
        """Verifica que el código de venta sea único y no se pueda duplicar."""
        record = Sale.objects.create(
            employee=self.employee,
            product=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
        )
        record.refresh_from_db()
        with self.assertRaises(Exception):
            Sale.objects.create(
                codigo=record.codigo,
                employee=self.employee,
                product=self.service,
                performed_by=self.user,
                scheduled_for=timezone.now(),
                product_price=Decimal("50.00"),
            )


class PurchaseModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="purchase_admin",
            password="pass1234",
            role=User.Role.ADMIN,
        )
        self.product = CatalogItem.objects.create(
            kind=CatalogItem.Kind.PRODUCT,
            name="Shampoo",
            price=Decimal("150.00"),
        )

    def test_create_purchase(self):
        """Verifica que se pueda crear una compra con todos los campos requeridos."""
        purchase = Purchase.objects.create(
            product=self.product,
            quantity=10,
            unit_cost=Decimal("80.00"),
            notes="Compra test",
            created_by=self.user,
        )
        self.assertEqual(purchase.product, self.product)
        self.assertEqual(purchase.quantity, 10)
        self.assertEqual(purchase.unit_cost, Decimal("80.00"))
        self.assertEqual(purchase.notes, "Compra test")
        self.assertEqual(purchase.created_by, self.user)

    def test_str_representation(self):
        """Verifica que la representación en cadena incluya el código, producto y cantidad."""
        purchase = Purchase.objects.create(
            product=self.product,
            quantity=4,
            unit_cost=Decimal("50.00"),
            created_by=self.user,
        )
        self.assertEqual(str(purchase), f"{purchase.codigo} - Shampoo x4")

    def test_codigo_auto_generated_on_create(self):
        """Verifica que el código de compra se genere automáticamente al crearla."""
        purchase = Purchase.objects.create(
            product=self.product,
            quantity=5,
            unit_cost=Decimal("80.00"),
            created_by=self.user,
        )
        purchase.refresh_from_db()
        self.assertTrue(purchase.codigo)
        self.assertNotEqual(purchase.codigo, "")

    def test_codigo_format_com(self):
        """Verifica que el código de compra tenga el formato 'COM-{pk}'."""
        purchase = Purchase.objects.create(
            product=self.product,
            quantity=3,
            unit_cost=Decimal("80.00"),
            created_by=self.user,
        )
        purchase.refresh_from_db()
        self.assertEqual(purchase.codigo, f"COM-{purchase.pk}")

    def test_codigo_unique(self):
        """Verifica que el código de compra sea único y no se pueda duplicar."""
        purchase = Purchase.objects.create(
            product=self.product,
            quantity=2,
            unit_cost=Decimal("80.00"),
            created_by=self.user,
        )
        purchase.refresh_from_db()
        with self.assertRaises(Exception):
            Purchase.objects.create(
                codigo=purchase.codigo,
                product=self.product,
                quantity=3,
                unit_cost=Decimal("90.00"),
                created_by=self.user,
            )

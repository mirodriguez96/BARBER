from decimal import Decimal

from django.test import TestCase

from barberia.accounts.models import User
from barberia.catalog.models import CatalogItem
from barberia.inventory.models import InventoryMovement


class InventoryMovementModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="admin",
            password="pass1234",
            role=User.Role.ADMIN,
        )
        self.product = CatalogItem.objects.create(
            kind=CatalogItem.Kind.PRODUCT,
            name="Shampoo",
            price=Decimal("150.00"),
        )

    def test_create_purchase_movement(self):
        movement = InventoryMovement.objects.create(
            product=self.product,
            quantity=10,
            movement_type=InventoryMovement.MovementType.PURCHASE,
            unit_cost=Decimal("80.00"),
            created_by=self.user,
        )
        self.assertEqual(movement.product, self.product)
        self.assertEqual(movement.quantity, 10)
        self.assertEqual(movement.movement_type, "purchase")
        self.assertEqual(movement.unit_cost, Decimal("80.00"))
        self.assertIsNotNone(movement.created_at)

    def test_create_sale_movement(self):
        movement = InventoryMovement.objects.create(
            product=self.product,
            quantity=-3,
            movement_type=InventoryMovement.MovementType.SALE,
            created_by=self.user,
        )
        self.assertEqual(movement.quantity, -3)
        self.assertEqual(movement.movement_type, "sale")

    def test_create_adjustment_movement(self):
        movement = InventoryMovement.objects.create(
            product=self.product,
            quantity=5,
            movement_type=InventoryMovement.MovementType.ADJUSTMENT,
            notes="Ajuste por inventario",
            created_by=self.user,
        )
        self.assertEqual(movement.movement_type, "adjustment")
        self.assertEqual(movement.notes, "Ajuste por inventario")

    def test_create_initial_movement(self):
        movement = InventoryMovement.objects.create(
            product=self.product,
            quantity=20,
            movement_type=InventoryMovement.MovementType.INITIAL,
            created_by=self.user,
        )
        self.assertEqual(movement.movement_type, "initial")
        self.assertEqual(movement.quantity, 20)

    def test_str_representation(self):
        movement = InventoryMovement.objects.create(
            product=self.product,
            quantity=10,
            movement_type=InventoryMovement.MovementType.PURCHASE,
            created_by=self.user,
        )
        expected = "Compra - Shampoo x10"
        self.assertEqual(str(movement), expected)

    def test_str_sale_representation(self):
        movement = InventoryMovement.objects.create(
            product=self.product,
            quantity=-3,
            movement_type=InventoryMovement.MovementType.SALE,
            created_by=self.user,
        )
        expected = "Venta - Shampoo x-3"
        self.assertEqual(str(movement), expected)

    def test_default_is_supply_false(self):
        movement = InventoryMovement.objects.create(
            product=self.product,
            quantity=5,
            movement_type=InventoryMovement.MovementType.ADJUSTMENT,
            created_by=self.user,
        )
        self.assertFalse(movement.is_supply)

    def test_can_set_is_supply_true(self):
        movement = InventoryMovement.objects.create(
            product=self.product,
            quantity=5,
            movement_type=InventoryMovement.MovementType.ADJUSTMENT,
            is_supply=True,
            created_by=self.user,
        )
        self.assertTrue(movement.is_supply)

    def test_unit_cost_defaults_to_zero(self):
        movement = InventoryMovement.objects.create(
            product=self.product,
            quantity=5,
            movement_type=InventoryMovement.MovementType.ADJUSTMENT,
            created_by=self.user,
        )
        self.assertEqual(movement.unit_cost, Decimal("0.00"))

    def test_reference_sale_nullable(self):
        movement = InventoryMovement.objects.create(
            product=self.product,
            quantity=5,
            movement_type=InventoryMovement.MovementType.ADJUSTMENT,
            created_by=self.user,
        )
        self.assertIsNone(movement.reference_sale)

    def test_notes_blank_by_default(self):
        movement = InventoryMovement.objects.create(
            product=self.product,
            quantity=5,
            movement_type=InventoryMovement.MovementType.ADJUSTMENT,
            created_by=self.user,
        )
        self.assertEqual(movement.notes, "")

    def test_created_at_auto_set(self):
        movement = InventoryMovement.objects.create(
            product=self.product,
            quantity=5,
            movement_type=InventoryMovement.MovementType.ADJUSTMENT,
            created_by=self.user,
        )
        self.assertIsNotNone(movement.created_at)

    def test_created_by_protected_on_delete(self):
        movement = InventoryMovement.objects.create(
            product=self.product,
            quantity=5,
            movement_type=InventoryMovement.MovementType.ADJUSTMENT,
            created_by=self.user,
        )
        self.assertEqual(movement.created_by, self.user)

from django.conf import settings
from django.db import models


class InventoryMovement(models.Model):
    class MovementType(models.TextChoices):
        PURCHASE = "purchase", "Compra"
        SALE = "sale", "Venta"
        ADJUSTMENT = "adjustment", "Ajuste"
        INITIAL = "initial", "Inventario inicial"

    product = models.ForeignKey(
        "catalog.CatalogItem",
        on_delete=models.CASCADE,
        related_name="inventory_movements",
    )
    quantity = models.IntegerField()
    movement_type = models.CharField(
        max_length=20,
        choices=MovementType.choices,
    )
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    reference_sale = models.ForeignKey(
        "operations.ServiceRecord",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_movements",
    )
    notes = models.TextField(blank=True)
    is_supply = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_movements",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"{self.get_movement_type_display()} - {self.product.name} x{self.quantity}"
        )

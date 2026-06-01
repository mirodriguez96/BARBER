from django.conf import settings
from django.db import models


class Sale(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Programado"
        IN_PROGRESS = "in_progress", "En proceso"
        DONE = "done", "Realizado"
        CANCELED = "canceled", "Cancelado"

    codigo = models.CharField("código", max_length=50, unique=True, blank=True)
    client = models.ForeignKey(
        "people.Client",
        on_delete=models.PROTECT,
        related_name="sales",
        null=True,
        blank=True,
    )
    employee = models.ForeignKey(
        "people.Employee",
        on_delete=models.PROTECT,
        related_name="sales",
        null=True,
        blank=True,
    )
    product = models.ForeignKey(
        "catalog.CatalogItem",
        on_delete=models.PROTECT,
        related_name="sales",
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="performed_sales",
    )
    scheduled_for = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED,
    )
    notes = models.TextField(blank=True)
    product_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    commission_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    tip_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"

    def __str__(self):
        client_label = self.client or "Cliente no registrado"
        return f"{self.codigo} - {client_label} - {self.product}"


class Purchase(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Activo"
        CANCELED = "canceled", "Anulado"

    codigo = models.CharField("código", max_length=50, unique=True, blank=True)
    product = models.ForeignKey(
        "catalog.CatalogItem",
        on_delete=models.PROTECT,
        related_name="purchases",
    )
    quantity = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="purchases",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    class Meta:
        verbose_name = "Compra"
        verbose_name_plural = "Compras"

    def __str__(self):
        return f"{self.codigo} - {self.product.name} x{self.quantity}"

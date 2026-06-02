import uuid

from django.db import models


class CatalogItem(models.Model):
    class Kind(models.TextChoices):
        SERVICE = "service", "Servicio"
        PRODUCT = "product", "Producto"

    kind = models.CharField(max_length=20, choices=Kind.choices)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    sku = models.CharField("código", max_length=50, unique=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    barber_commission_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )
    duration_minutes = models.PositiveIntegerField(
        "duración (minutos)",
        blank=True,
        null=True,
        help_text="Solo para servicios. Define el bloque de tiempo en la agenda.",
    )
    current_stock = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        is_new = not self.pk
        if is_new:
            temp_sku = f"TMP-{uuid.uuid4().hex[:12].upper()}"
            self.sku = temp_sku
        super().save(*args, **kwargs)
        if is_new:
            prefix = "PROD" if self.kind == self.Kind.PRODUCT else "SERV"
            self.sku = f"{prefix}-{self.pk}"
            CatalogItem.objects.filter(pk=self.pk).update(sku=self.sku)

    def __str__(self):
        return self.name

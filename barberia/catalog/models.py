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
    current_stock = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.sku:
            import uuid

            self.sku = f"TMP-{uuid.uuid4().hex[:12].upper()}"
            super().save(*args, **kwargs)
            prefix = "PROD" if self.kind == self.Kind.PRODUCT else "SERV"
            self.sku = f"{prefix}-{self.pk}"
            CatalogItem.objects.filter(pk=self.pk).update(sku=self.sku)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return self.name

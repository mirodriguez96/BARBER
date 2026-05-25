from django.db import models


class CatalogItem(models.Model):
    class Kind(models.TextChoices):
        SERVICE = "service", "Servicio"
        PRODUCT = "product", "Producto"

    kind = models.CharField(max_length=20, choices=Kind.choices)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    sku = models.CharField(max_length=50, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    barber_commission_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

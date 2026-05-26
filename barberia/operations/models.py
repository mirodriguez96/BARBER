from django.conf import settings
from django.db import models


class ServiceRecord(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Programado"
        IN_PROGRESS = "in_progress", "En proceso"
        DONE = "done", "Realizado"
        CANCELED = "canceled", "Cancelado"

    client = models.ForeignKey(
        "people.Client",
        on_delete=models.PROTECT,
        related_name="service_records",
        null=True,
        blank=True,
    )
    barber = models.ForeignKey(
        "people.Employee", on_delete=models.PROTECT, related_name="service_records",
    )
    service = models.ForeignKey(
        "catalog.CatalogItem", on_delete=models.PROTECT, related_name="service_records",
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="performed_services",
    )
    scheduled_for = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SCHEDULED,
    )
    notes = models.TextField(blank=True)
    service_price = models.DecimalField(max_digits=10, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tip_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
    )

    def __str__(self):
        client_label = self.client or "Cliente no registrado"
        return f"{client_label} - {self.service}"

from django.core.validators import RegexValidator
from django.db import models


class Company(models.Model):
    nit = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True, default="")
    phone = models.CharField(max_length=20, blank=True, default="")
    logo = models.ImageField(upload_to="logos/", blank=True)
    opening_time = models.TimeField(
        "hora de apertura",
        default="09:00",
    )
    closing_time = models.TimeField(
        "hora de cierre",
        default="19:00",
    )

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"

    def __str__(self):
        return self.name

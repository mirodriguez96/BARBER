from django.core.exceptions import ValidationError
from django.db import models


class Company(models.Model):
    nit = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=200)

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"

    def __str__(self):
        return self.name

    def clean(self):
        if not self.pk and Company.objects.exists():
            raise ValidationError("Solo se permite registrar una empresa.")

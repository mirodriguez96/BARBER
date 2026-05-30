from django.db import models


class Tenant(models.Model):
    schema_name = models.SlugField(
        max_length=63,
        unique=True,
        help_text="Identificador usado en el subdominio. Ej: 'luxor'",
    )
    db_name = models.CharField(
        max_length=63,
        unique=True,
        help_text="Nombre de la base de datos PostgreSQL. Ej: 'barber_luxor'",
    )
    name = models.CharField(max_length=200, help_text="Nombre comercial de la empresa")
    nit = models.CharField(max_length=30, unique=True, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"

    def __str__(self):
        return f"{self.name} ({self.schema_name})"


class Domain(models.Model):
    domain = models.CharField(
        max_length=253,
        unique=True,
        help_text="Subdominio completo. Ej: luxor.colstyle.com",
    )
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="domains")
    is_primary = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Dominio"
        verbose_name_plural = "Dominios"

    def __str__(self):
        return self.domain

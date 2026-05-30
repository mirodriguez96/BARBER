from django.apps import AppConfig


class TenantsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "barberia.tenants"
    verbose_name = "Gestión de Empresas"

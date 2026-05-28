from django.contrib import admin

from .models import Domain, Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("schema_name", "name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("schema_name", "name", "nit")
    prepopulated_fields = {"schema_name": ("name",)}


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ("domain", "tenant", "is_primary")
    list_filter = ("is_primary",)
    search_fields = ("domain", "tenant__name")

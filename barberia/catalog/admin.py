from django.contrib import admin

from .models import CatalogItem


@admin.register(CatalogItem)
class CatalogItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "sku",
        "name",
        "kind",
        "price",
        "barber_commission_percent",
        "is_active",
    )
    list_filter = ("kind", "is_active")
    search_fields = ("name", "sku", "description")
    list_editable = ("price", "barber_commission_percent", "is_active")

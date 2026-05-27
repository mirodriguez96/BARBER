from django.contrib import admin

from .models import InventoryMovement


@admin.register(InventoryMovement)
class InventoryMovementAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "movement_type",
        "quantity",
        "is_supply",
        "unit_cost",
        "created_by",
        "created_at",
    )
    list_filter = ("movement_type", "created_at")
    search_fields = ("product__name", "notes")
    autocomplete_fields = ("product", "reference_sale", "created_by")

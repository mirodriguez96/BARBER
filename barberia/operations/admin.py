from django.contrib import admin

from .models import Purchase, Sale


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = (
        "codigo",
        "client",
        "employee",
        "product",
        "status",
        "scheduled_for",
        "product_price",
        "quantity",
        "commission_amount",
        "tip_amount",
    )
    list_filter = ("status", "scheduled_for", "employee")
    search_fields = (
        "codigo",
        "client__full_name",
        "employee__full_name",
        "product__name",
        "notes",
    )
    autocomplete_fields = ("client", "employee", "product", "performed_by")


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = (
        "codigo",
        "product",
        "quantity",
        "unit_cost",
        "created_by",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = ("codigo", "product__name", "notes")
    autocomplete_fields = ("product", "created_by")

from django.contrib import admin

from .models import Sale


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = (
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
    search_fields = ("client__full_name", "employee__full_name", "product__name", "notes")
    autocomplete_fields = ("client", "employee", "product", "performed_by")

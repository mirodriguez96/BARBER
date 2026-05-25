from django.contrib import admin

from .models import ServiceRecord


@admin.register(ServiceRecord)
class ServiceRecordAdmin(admin.ModelAdmin):
    list_display = (
        "client",
        "barber",
        "service",
        "status",
        "scheduled_for",
        "service_price",
        "commission_amount",
        "tip_amount",
    )
    list_filter = ("status", "scheduled_for", "barber")
    search_fields = ("client__full_name", "barber__full_name", "service__name", "notes")
    autocomplete_fields = ("client", "barber", "service", "performed_by")

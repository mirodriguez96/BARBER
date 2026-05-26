from django.contrib import admin

from .models import Client, Employee


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "document_id",
        "phone",
        "email",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "created_at")
    search_fields = ("full_name", "document_id", "phone", "email")
    autocomplete_fields = ("user",)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("full_name", "document_id", "phone", "birth_date", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("full_name", "document_id", "phone")

from django.contrib import admin

from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "nit", "opening_time", "closing_time")
    search_fields = ("name", "nit")

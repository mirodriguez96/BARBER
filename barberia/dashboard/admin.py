from django.contrib import admin

from .models import RoleCrudPermission, RoleMenuPermission


@admin.register(RoleMenuPermission)
class RoleMenuPermissionAdmin(admin.ModelAdmin):
    list_display = ("role", "menu_key")
    list_filter = ("role", "menu_key")
    search_fields = ("role", "menu_key")
    ordering = ("role", "menu_key")


@admin.register(RoleCrudPermission)
class RoleCrudPermissionAdmin(admin.ModelAdmin):
    list_display = ("role", "app_key", "action")
    list_filter = ("role", "app_key", "action")
    search_fields = ("role", "app_key", "action")
    ordering = ("role", "app_key", "action")

from django.db import models

from barberia.accounts.models import User


class RoleMenuPermission(models.Model):
    role = models.CharField(max_length=20, choices=User.Role.choices)
    menu_key = models.CharField(max_length=50)

    class Meta:
        unique_together = ("role", "menu_key")
        verbose_name = "Permiso de menú por rol"
        verbose_name_plural = "Permisos de menú por rol"

    def __str__(self):
        return f"{self.role} -> {self.menu_key}"


class RoleCrudPermission(models.Model):
    class AppKey(models.TextChoices):
        PERSONAL = "personal", "Personal"
        PRODUCTOS = "productos", "Productos"
        VENTAS = "ventas", "Ventas"
        COMPRAS = "compras", "Compras"
        INVENTARIO = "inventario", "Inventario"

    class Action(models.TextChoices):
        REGISTRAR = "registrar", "Registrar"
        MODIFICAR = "modificar", "Modificar"
        DESACTIVAR = "desactivar", "Desactivar"
        AJUSTAR = "ajustar", "Ajustar"

    role = models.CharField(max_length=20, choices=User.Role.choices)
    app_key = models.CharField(max_length=20, choices=AppKey.choices)
    action = models.CharField(max_length=20, choices=Action.choices)

    class Meta:
        unique_together = ("role", "app_key", "action")
        verbose_name = "Permiso de acción por rol"
        verbose_name_plural = "Permisos de acción por rol"

    def __str__(self):
        return f"{self.role} -> {self.app_key}:{self.action}"

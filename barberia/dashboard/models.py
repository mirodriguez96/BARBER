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

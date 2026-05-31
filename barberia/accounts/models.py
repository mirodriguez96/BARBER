from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        BARBERO = "barbero", "Barbero"
        ESTILISTA = "estilista", "Estilista"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.ADMIN)
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.get_full_name() or self.username

from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Employee(TimeStampedModel):
    class WeekDay(models.IntegerChoices):
        MONDAY = 0, "Lunes"
        TUESDAY = 1, "Martes"
        WEDNESDAY = 2, "Miércoles"
        THURSDAY = 3, "Jueves"
        FRIDAY = 4, "Viernes"
        SATURDAY = 5, "Sábado"
        SUNDAY = 6, "Domingo"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    full_name = models.CharField(max_length=160)
    document_id = models.CharField(max_length=30, unique=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    day_off = models.IntegerField(
        choices=WeekDay.choices,
        null=True,
        blank=True,
        verbose_name="día de descanso",
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.full_name


class Client(TimeStampedModel):
    full_name = models.CharField(max_length=160)
    document_id = models.CharField(
        "documento / cédula",
        max_length=30,
        unique=True,
        blank=True,
        null=True,
        help_text="Opcional para reservas en línea. Si se llena, debe ser único.",
    )
    phone = models.CharField(max_length=20)
    email = models.EmailField("correo electrónico", blank=True)
    birth_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.full_name

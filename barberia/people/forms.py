from django import forms
from django.contrib.auth import get_user_model

from barberia.common.forms import DashboardModelForm

from .models import Client, Employee


class BarberForm(DashboardModelForm):
    role = forms.ChoiceField(
        choices=[],
        label="Rol",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = Employee
        fields = [
            "user",
            "full_name",
            "document_id",
            "phone",
            "email",
            "day_off",
            "is_active",
        ]
        labels = {
            "user": "Usuario",
            "full_name": "Nombre completo",
            "document_id": "Documento / cédula",
            "phone": "Teléfono",
            "email": "Correo electrónico",
            "day_off": "Día de descanso",
            "is_active": "Activo",
        }
        widgets = {
            "user": forms.Select(attrs={"class": "form-select"}),
            "full_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej. Juan Pérez"},
            ),
            "document_id": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej. 1020304050"},
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej. 300 123 4567"},
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "correo@ejemplo.com"},
            ),
            "day_off": forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        User = get_user_model()
        self.fields["role"].choices = User.Role.choices
        if self.user and self.user.role != User.Role.ADMIN:
            self.fields["role"].choices = [
                c for c in User.Role.choices if c[0] != User.Role.ADMIN
            ]
        self.fields["user"].required = True
        self.fields["user"].queryset = User.objects.exclude(employee__isnull=False)
        if self.user and self.user.role != User.Role.ADMIN:
            self.fields["user"].queryset = self.fields["user"].queryset.exclude(
                role=User.Role.ADMIN
            )
        if self.instance and self.instance.pk and self.instance.user_id:
            self.fields["user"].queryset = (
                User.objects.filter(pk=self.instance.user_id)
                | self.fields["user"].queryset
            )
            self.fields["role"].initial = self.instance.user.role

    def save(self, commit=True):
        instance = super().save(commit=commit)
        if commit and instance.user_id:
            user = instance.user
            user.role = self.cleaned_data["role"]
            user.save(update_fields=["role"])
        return instance

    def clean_document_id(self):
        document_id = self.cleaned_data["document_id"].strip()
        existing = Employee.objects.filter(document_id=document_id)
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise forms.ValidationError("Ya existe un colaborador con ese documento.")
        return document_id

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        if not phone:
            raise forms.ValidationError("El teléfono es obligatorio.")
        return phone


class BarberEditForm(DashboardModelForm):
    role = forms.ChoiceField(
        choices=[],
        label="Rol",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = Employee
        fields = ["full_name", "phone", "email", "day_off"]
        labels = {
            "full_name": "Nombre completo",
            "phone": "Teléfono",
            "email": "Correo electrónico",
            "day_off": "Día de descanso",
        }
        widgets = {
            "full_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej. Juan Pérez"},
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej. 300 123 4567"},
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "correo@ejemplo.com"},
            ),
            "day_off": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        User = get_user_model()
        self.fields["role"].choices = User.Role.choices
        if self.instance and self.instance.pk and self.instance.user_id:
            self.fields["role"].initial = self.instance.user.role

    def save(self, commit=True):
        instance = super().save(commit=commit)
        if commit and instance.user_id:
            user = instance.user
            user.role = self.cleaned_data["role"]
            user.save(update_fields=["role"])
        return instance

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        if not phone:
            raise forms.ValidationError("El teléfono es obligatorio.")
        return phone


class ClientForm(DashboardModelForm):
    class Meta:
        model = Client
        fields = ["full_name", "document_id", "phone", "birth_date", "is_active"]
        labels = {
            "full_name": "Nombre completo",
            "document_id": "Documento / cédula",
            "phone": "Teléfono",
            "birth_date": "Fecha de nacimiento",
            "is_active": "Activo",
        }
        widgets = {
            "full_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej. María García"},
            ),
            "document_id": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej. 1020304050"},
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej. 300 123 4567"},
            ),
            "birth_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_document_id(self):
        document_id = self.cleaned_data.get("document_id")
        if not document_id or not document_id.strip():
            raise forms.ValidationError("El documento / cédula es obligatorio.")
        document_id = document_id.strip()
        existing = Client.objects.filter(document_id=document_id)
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise forms.ValidationError("Ya existe un cliente con ese documento.")
        return document_id

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        if not phone:
            raise forms.ValidationError("El teléfono es obligatorio.")
        return phone


class ClientEditForm(DashboardModelForm):
    class Meta:
        model = Client
        fields = ["full_name", "document_id", "phone", "email", "birth_date"]
        labels = {
            "full_name": "Nombre completo",
            "document_id": "Documento / cédula",
            "phone": "Teléfono",
            "email": "Correo electrónico",
            "birth_date": "Fecha de nacimiento",
        }
        widgets = {
            "full_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej. María García"},
            ),
            "document_id": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej. 1020304050"},
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej. 300 123 4567"},
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "correo@ejemplo.com"},
            ),
            "birth_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
            ),
        }

    def clean_document_id(self):
        document_id = self.cleaned_data.get("document_id")
        if not document_id or not document_id.strip():
            raise forms.ValidationError("El documento / cédula es obligatorio.")
        document_id = document_id.strip()
        existing = Client.objects.filter(document_id=document_id)
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise forms.ValidationError("Ya existe un cliente con ese documento.")
        return document_id

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        if not phone:
            raise forms.ValidationError("El teléfono es obligatorio.")
        return phone

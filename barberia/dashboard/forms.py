from django import forms
from django.contrib.auth import get_user_model

from barberia.catalog.models import CatalogItem
from barberia.common.forms import DashboardModelForm
from barberia.common.models import Company
from barberia.inventory.models import InventoryMovement
from barberia.operations.models import Purchase
from barberia.people.models import Client, Employee


class CompanyForm(DashboardModelForm):
    class Meta:
        model = Company
        fields = ["nit", "name", "logo"]
        labels = {
            "nit": "NIT",
            "name": "Nombre de la empresa",
            "logo": "Logo de la empresa",
        }
        widgets = {
            "nit": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej. 900123456-7"}
            ),
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej. Barbería Central"}
            ),
            "logo": forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": "image/*"}
            ),
        }


class BookingConfigForm(DashboardModelForm):
    class Meta:
        model = Company
        fields = ["opening_time", "closing_time"]
        labels = {
            "opening_time": "Hora de apertura",
            "closing_time": "Hora de cierre",
        }
        widgets = {
            "opening_time": forms.TimeInput(attrs={"type": "time"}),
            "closing_time": forms.TimeInput(attrs={"type": "time"}),
        }


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


class InventoryPurchaseForm(DashboardModelForm):
    class Meta:
        model = Purchase
        fields = [
            "product",
            "quantity",
            "unit_cost",
            "notes",
        ]
        labels = {
            "product": "Producto",
            "quantity": "Cantidad",
            "unit_cost": "Costo unitario",
            "notes": "Observaciones",
        }
        widgets = {
            "product": forms.Select(attrs={"class": "form-select"}),
            "quantity": forms.NumberInput(
                attrs={"class": "form-control", "min": "1", "step": "1"},
            ),
            "unit_cost": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"},
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Observaciones de la compra",
                },
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = CatalogItem.objects.filter(
            is_active=True,
            kind=CatalogItem.Kind.PRODUCT,
        )


class PurchaseForm(InventoryPurchaseForm):
    pass


class PurchaseEditForm(DashboardModelForm):
    class Meta:
        model = Purchase
        fields = [
            "quantity",
            "unit_cost",
            "notes",
        ]
        labels = {
            "quantity": "Cantidad",
            "unit_cost": "Costo unitario",
            "notes": "Observaciones",
        }
        widgets = {
            "quantity": forms.NumberInput(
                attrs={"class": "form-control", "min": "1", "step": "1"},
            ),
            "unit_cost": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"},
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Observaciones de la compra",
                },
            ),
        }


class InventoryAdjustForm(DashboardModelForm):
    class Meta:
        model = InventoryMovement
        fields = [
            "product",
            "quantity",
            "is_supply",
            "notes",
        ]
        labels = {
            "product": "Producto",
            "quantity": "Cantidad",
            "is_supply": "Insumo",
            "notes": "Motivo / observaciones",
        }
        widgets = {
            "product": forms.Select(attrs={"class": "form-select"}),
            "quantity": forms.NumberInput(
                attrs={"class": "form-control", "step": "1"},
            ),
            "is_supply": forms.CheckboxInput(
                attrs={"class": "form-check-input"},
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Motivo del ajuste",
                },
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = CatalogItem.objects.filter(
            is_active=True,
            kind=CatalogItem.Kind.PRODUCT,
        )
        self.fields["quantity"].help_text = (
            "Usa valores positivos para aumentar stock, "
            "negativos para disminuir. Si marcas 'Insumo' "
            "se guardará automáticamente como negativo."
        )

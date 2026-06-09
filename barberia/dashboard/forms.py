from django import forms

from barberia.catalog.models import CatalogItem
from barberia.common.forms import DashboardModelForm
from barberia.common.models import Company
from barberia.inventory.models import InventoryMovement
from barberia.operations.models import Purchase


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

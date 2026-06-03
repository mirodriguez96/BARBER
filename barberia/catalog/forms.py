from decimal import Decimal

from django import forms

from barberia.catalog.models import CatalogItem
from barberia.common.forms import DashboardModelForm


class ServiceCatalogSelect(forms.Select):
    queryset = None

    def create_option(
        self, name, value, label, selected, index, subindex=None, attrs=None
    ):
        option = super().create_option(
            name, value, label, selected, index, subindex, attrs
        )
        raw_value = getattr(value, "value", value)
        if raw_value and self.queryset is not None:
            item = self.queryset.filter(pk=raw_value).first()
            if item:
                option["attrs"]["data-price"] = str(item.price)
                option["attrs"]["data-commission"] = str(item.barber_commission_percent)
        return option


class CatalogCommissionMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._adjust_fields_for_kind()

    def _adjust_fields_for_kind(self):
        kind_value = None
        if self.is_bound:
            kind_value = self.data.get(self.add_prefix("kind"))
        elif self.instance and self.instance.pk:
            kind_value = self.instance.kind
        if kind_value == CatalogItem.Kind.PRODUCT:
            self.fields["barber_commission_percent"].disabled = True
            self.fields["barber_commission_percent"].initial = Decimal("0.00")
            if "duration_minutes" in self.fields:
                self.fields["duration_minutes"].disabled = True
                self.fields["duration_minutes"].widget.attrs[
                    "placeholder"
                ] = "Solo para servicios"

    def clean(self):
        cleaned_data = super().clean()
        kind = cleaned_data.get("kind")
        if kind == CatalogItem.Kind.PRODUCT:
            cleaned_data["barber_commission_percent"] = Decimal("0.00")
            cleaned_data["duration_minutes"] = None
        return cleaned_data


class CatalogItemForm(CatalogCommissionMixin, DashboardModelForm):
    class Meta:
        model = CatalogItem
        fields = [
            "name",
            "kind",
            "price",
            "duration_minutes",
            "barber_commission_percent",
            "is_active",
            "description",
        ]
        labels = {
            "kind": "Tipo",
            "name": "Nombre",
            "price": "Precio",
            "duration_minutes": "Duración (min)",
            "barber_commission_percent": "Comisión del colaborador (%)",
            "is_active": "Activo",
        }
        widgets = {
            "kind": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej. Corte degradado"},
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Detalle del producto o servicio",
                },
            ),
            "price": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"},
            ),
            "duration_minutes": forms.NumberInput(
                attrs={"class": "form-control", "min": "0", "placeholder": "Ej. 30"},
            ),
            "barber_commission_percent": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"},
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class CatalogItemEditForm(CatalogCommissionMixin, DashboardModelForm):
    class Meta:
        model = CatalogItem
        fields = [
            "name",
            "kind",
            "price",
            "duration_minutes",
            "barber_commission_percent",
            "description",
        ]
        labels = {
            "kind": "Tipo",
            "name": "Nombre",
            "description": "Descripción",
            "price": "Precio",
            "duration_minutes": "Duración (min)",
            "barber_commission_percent": "Comisión del colaborador (%)",
        }
        widgets = {
            "kind": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej. Corte degradado"},
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Detalle del producto o servicio",
                },
            ),
            "price": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"},
            ),
            "duration_minutes": forms.NumberInput(
                attrs={"class": "form-control", "min": "0", "placeholder": "Ej. 30"},
            ),
            "barber_commission_percent": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"},
            ),
        }

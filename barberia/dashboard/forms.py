from decimal import Decimal

from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone

from barberia.catalog.models import CatalogItem
from barberia.operations.models import ServiceRecord
from barberia.people.models import Employee


class DashboardModelForm(forms.ModelForm):
    def _bootstrapify_fields(self):
        for name, field in self.fields.items():
            widget = field.widget
            base_classes = widget.attrs.get("class", "")

            if isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
                widget.attrs["class"] = f"{base_classes} form-check-input".strip()
                continue

            if isinstance(widget, forms.Select):
                widget.attrs["class"] = (
                    f"{base_classes} form-select form-select-lg".strip()
                )
            else:
                widget.attrs["class"] = (
                    f"{base_classes} form-control form-control-lg".strip()
                )

            widget.attrs.setdefault("autocomplete", "off")
            widget.attrs.setdefault("spellcheck", "false")

            if name in {"notes", "description"}:
                widget.attrs["class"] = (
                    f"{widget.attrs['class']} dashboard-textarea".strip()
                )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self._bootstrapify_fields()


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
            service = self.queryset.filter(pk=raw_value).first()
            if service:
                option["attrs"]["data-price"] = str(service.price)
                option["attrs"]["data-commission"] = str(
                    service.barber_commission_percent
                )
        return option


class BarberForm(DashboardModelForm):
    class Meta:
        model = Employee
        fields = ["user", "full_name", "document_id", "phone", "email", "is_active"]
        labels = {
            "user": "Usuario",
            "full_name": "Nombre completo",
            "document_id": "Documento / cédula",
            "phone": "Teléfono",
            "email": "Correo electrónico",
            "is_active": "Activo",
        }
        widgets = {
            "user": forms.Select(attrs={"class": "form-select"}),
            "full_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej. Juan Pérez"}
            ),
            "document_id": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej. 1020304050"}
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej. 300 123 4567"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "correo@ejemplo.com"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        User = get_user_model()
        self.fields["user"].queryset = User.objects.exclude(employee__isnull=False)
        if self.instance and self.instance.pk and self.instance.user_id:
            self.fields["user"].queryset = (
                User.objects.filter(pk=self.instance.user_id)
                | self.fields["user"].queryset
            )

    def clean_document_id(self):
        document_id = self.cleaned_data["document_id"].strip()
        existing = Employee.objects.filter(document_id=document_id)
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise forms.ValidationError("Ya existe un barbero con ese documento.")
        return document_id

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        if not phone:
            raise forms.ValidationError("El teléfono es obligatorio.")
        return phone


class BarberEditForm(DashboardModelForm):
    class Meta:
        model = Employee
        fields = ["full_name", "phone", "email"]
        labels = {
            "full_name": "Nombre completo",
            "phone": "Teléfono",
            "email": "Correo electrónico",
        }
        widgets = {
            "full_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej. Juan Pérez"}
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej. 300 123 4567"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "correo@ejemplo.com"}
            ),
        }

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        if not phone:
            raise forms.ValidationError("El teléfono es obligatorio.")
        return phone


class CatalogCommissionMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._adjust_commission_for_kind()

    def _adjust_commission_for_kind(self):
        kind_value = None
        if self.is_bound:
            kind_value = self.data.get(self.add_prefix("kind"))
        elif self.instance and self.instance.pk:
            kind_value = self.instance.kind
        if kind_value == CatalogItem.Kind.PRODUCT:
            self.fields["barber_commission_percent"].disabled = True
            self.fields["barber_commission_percent"].initial = Decimal("0.00")

    def clean(self):
        cleaned_data = super().clean()
        kind = cleaned_data.get("kind")
        if kind == CatalogItem.Kind.PRODUCT:
            cleaned_data["barber_commission_percent"] = Decimal("0.00")
        return cleaned_data


class CatalogItemForm(CatalogCommissionMixin, DashboardModelForm):
    class Meta:
        model = CatalogItem
        fields = [
            "sku",
            "name",
            "kind",
            "price",
            "barber_commission_percent",
            "is_active",
            "description",
        ]
        labels = {
            "kind": "Tipo",
            "name": "Nombre",
            "description": "Descripción",
            "sku": "Código / SKU",
            "price": "Precio",
            "barber_commission_percent": "Comisión del barbero (%)",
            "is_active": "Activo",
        }
        widgets = {
            "kind": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej. Corte degradado"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Detalle del producto o servicio",
                }
            ),
            "sku": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej. PROD-001"}
            ),
            "price": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "barber_commission_percent": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class CatalogItemEditForm(CatalogCommissionMixin, DashboardModelForm):
    class Meta:
        model = CatalogItem
        fields = ["name", "kind", "price", "barber_commission_percent", "description"]
        labels = {
            "kind": "Tipo",
            "name": "Nombre",
            "description": "Descripción",
            "price": "Precio",
            "barber_commission_percent": "Comisión del barbero (%)",
        }
        widgets = {
            "kind": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej. Corte degradado"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Detalle del producto o servicio",
                }
            ),
            "price": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "barber_commission_percent": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
        }


class ServiceRecordForm(DashboardModelForm):
    class Meta:
        model = ServiceRecord
        fields = [
            "barber",
            "client",
            "scheduled_for",
            "service",
            "service_price",
            "commission_amount",
            "tip_amount",
            "notes",
        ]
        labels = {
            "client": "Cliente",
            "barber": "Barbero",
            "service": "Servicio",
            "scheduled_for": "Fecha y hora",
            "notes": "Observaciones",
            "service_price": "Valor del servicio",
            "commission_amount": "Comisión",
            "tip_amount": "Propina",
        }
        widgets = {
            "client": forms.Select(attrs={"class": "form-select"}),
            "barber": forms.Select(attrs={"class": "form-select"}),
            "service": ServiceCatalogSelect(
                attrs={"class": "form-select", "data-service-selector": "true"}
            ),
            "scheduled_for": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Observaciones del servicio",
                }
            ),
            "service_price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "readonly": "readonly",
                }
            ),
            "commission_amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "readonly": "readonly",
                }
            ),
            "tip_amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "Opcional",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["client"].required = False
        self.fields["client"].empty_label = "Cliente no registrado"
        self.fields["client"].widget.attrs["aria-label"] = "Cliente opcional"
        if self.user and hasattr(self.user, "employee"):
            self.fields["barber"].queryset = Employee.objects.filter(
                pk=self.user.employee.pk, is_active=True
            )
        else:
            self.fields["barber"].queryset = Employee.objects.filter(is_active=True)
        self.fields["service"].queryset = CatalogItem.objects.filter(is_active=True)
        self.fields["service"].widget.queryset = self.fields["service"].queryset
        self.fields["scheduled_for"].initial = timezone.localtime(
            timezone.now()
        ).strftime("%Y-%m-%dT%H:%M")
        self.fields["service_price"].initial = self._service_price_initial()
        self.fields["commission_amount"].initial = self._commission_initial()
        self.fields["service_price"].disabled = True
        self.fields["commission_amount"].disabled = True

    def _selected_service(self):
        service = None
        if self.is_bound:
            service_id = self.data.get(self.add_prefix("service"))
            if service_id:
                service = self.fields["service"].queryset.filter(pk=service_id).first()
        elif self.instance and self.instance.pk and self.instance.service_id:
            service = self.instance.service
        return service

    def _service_price_initial(self):
        service = self._selected_service()
        return service.price if service else None

    def _commission_initial(self):
        service = self._selected_service()
        return service.barber_commission_percent if service else None


class ServiceRecordEditForm(DashboardModelForm):
    class Meta:
        model = ServiceRecord
        fields = [
            "barber",
            "service",
            "service_price",
            "commission_amount",
            "tip_amount",
        ]
        labels = {
            "barber": "Barbero",
            "service": "Servicio",
            "service_price": "Valor del servicio",
            "commission_amount": "Comisión",
            "tip_amount": "Propina",
        }
        widgets = {
            "barber": forms.Select(attrs={"class": "form-select"}),
            "service": ServiceCatalogSelect(
                attrs={"class": "form-select", "data-service-selector": "true"}
            ),
            "service_price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "readonly": "readonly",
                }
            ),
            "commission_amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "readonly": "readonly",
                }
            ),
            "tip_amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "Opcional",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.user and hasattr(self.user, "employee"):
            self.fields["barber"].queryset = Employee.objects.filter(
                pk=self.user.employee.pk, is_active=True
            )
        else:
            self.fields["barber"].queryset = Employee.objects.filter(is_active=True)
        self.fields["service"].queryset = CatalogItem.objects.filter(is_active=True)
        self.fields["service"].widget.queryset = self.fields["service"].queryset
        self.fields["service_price"].initial = self._service_price_initial()
        self.fields["commission_amount"].initial = self._commission_initial()
        self.fields["service_price"].disabled = True
        self.fields["commission_amount"].disabled = True

    def _selected_service(self):
        service = None
        if self.is_bound:
            service_id = self.data.get(self.add_prefix("service"))
            if service_id:
                service = self.fields["service"].queryset.filter(pk=service_id).first()
        elif self.instance and self.instance.pk and self.instance.service_id:
            service = self.instance.service
        return service

    def _service_price_initial(self):
        service = self._selected_service()
        return service.price if service else None

    def _commission_initial(self):
        service = self._selected_service()
        return service.barber_commission_percent if service else None

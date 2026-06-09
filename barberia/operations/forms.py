from django import forms
from django.utils import timezone

from barberia.catalog.forms import ServiceCatalogSelect
from barberia.catalog.models import CatalogItem
from barberia.common.forms import DashboardModelForm
from barberia.operations.models import Sale
from barberia.people.models import Employee


class SaleForm(DashboardModelForm):
    product_price = forms.DecimalField(
        label="Valor del servicio",
        widget=forms.NumberInput(attrs={"readonly": "readonly"}),
        required=False,
    )
    commission_amount = forms.DecimalField(
        label="Comisión del colaborador",
        widget=forms.NumberInput(attrs={"readonly": "readonly"}),
        required=False,
    )

    class Meta:
        model = Sale
        fields = [
            "employee",
            "client",
            "scheduled_for",
            "product",
            "product_price",
            "commission_amount",
            "tip_amount",
            "notes",
        ]
        labels = {
            "client": "Cliente",
            "employee": "Colaborador",
            "product": "Servicio",
            "scheduled_for": "Fecha y hora",
            "notes": "Observaciones",
            "product_price": "Valor del servicio",
            "commission_amount": "Comisión del colaborador",
            "tip_amount": "Propina",
        }
        widgets = {
            "client": forms.Select(attrs={"class": "form-select"}),
            "employee": forms.Select(attrs={"class": "form-select"}),
            "product": ServiceCatalogSelect(
                attrs={"class": "form-select", "data-service-selector": "true"},
            ),
            "scheduled_for": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Observaciones del servicio",
                },
            ),
            "commission_amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "readonly": "readonly",
                },
            ),
            "tip_amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "Opcional",
                },
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["client"].required = False
        self.fields["client"].empty_label = "Cliente no registrado"
        self.fields["client"].widget.attrs["aria-label"] = "Cliente opcional"
        if self.user and self.user.role == "admin":
            self.fields["employee"].queryset = Employee.objects.filter(is_active=True)
        elif self.user:
            try:
                employee = self.user.employee
                self.fields["employee"].queryset = Employee.objects.filter(
                    pk=employee.pk,
                    is_active=True,
                )
            except Exception:
                self.fields["employee"].queryset = Employee.objects.filter(
                    is_active=True,
                )
        else:
            self.fields["employee"].queryset = Employee.objects.filter(is_active=True)
        self.fields["employee"].required = True
        self.fields["employee"].widget.attrs["required"] = True
        self.fields["product"].queryset = CatalogItem.objects.filter(
            is_active=True,
            kind=CatalogItem.Kind.SERVICE,
        )
        self.fields["product"].widget.queryset = self.fields["product"].queryset
        self.fields["scheduled_for"].initial = timezone.localtime(
            timezone.now(),
        ).strftime("%Y-%m-%dT%H:%M")
        self.fields["product_price"].initial = self._product_price_initial()
        self.fields["commission_amount"].initial = self._commission_initial()
        self.fields["product_price"].disabled = True
        self.fields["commission_amount"].disabled = True

    def _selected_product(self):
        product = None
        if self.is_bound:
            product_id = self.data.get(self.add_prefix("product"))
            if product_id:
                product = self.fields["product"].queryset.filter(pk=product_id).first()
        elif self.instance and self.instance.pk and self.instance.product_id:
            product = self.instance.product
        return product

    def _product_price_initial(self):
        product = self._selected_product()
        return product.price if product else None

    def _commission_initial(self):
        product = self._selected_product()
        return product.barber_commission_percent if product else None


class SaleEditForm(DashboardModelForm):
    product_price = forms.DecimalField(
        label="Valor del servicio",
        widget=forms.NumberInput(attrs={"readonly": "readonly"}),
        required=False,
    )
    commission_amount = forms.DecimalField(
        label="Comisión del colaborador",
        widget=forms.NumberInput(attrs={"readonly": "readonly"}),
        required=False,
    )

    class Meta:
        model = Sale
        fields = [
            "employee",
            "product",
            "product_price",
            "commission_amount",
            "tip_amount",
            "notes",
        ]
        labels = {
            "employee": "Colaborador",
            "product": "Servicio",
            "product_price": "Valor del servicio",
            "commission_amount": "Comisión del colaborador",
            "tip_amount": "Propina",
            "notes": "Observaciones",
        }
        widgets = {
            "employee": forms.Select(attrs={"class": "form-select"}),
            "product": ServiceCatalogSelect(
                attrs={"class": "form-select", "data-service-selector": "true"},
            ),
            "tip_amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "Opcional",
                },
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Observaciones del servicio",
                },
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.user and hasattr(self.user, "employee"):
            self.fields["employee"].queryset = Employee.objects.filter(
                pk=self.user.employee.pk,
                is_active=True,
            )
        else:
            self.fields["employee"].queryset = Employee.objects.filter(is_active=True)
        self.fields["employee"].required = True
        self.fields["employee"].widget.attrs["required"] = True
        self.fields["product"].queryset = CatalogItem.objects.filter(
            is_active=True,
            kind=CatalogItem.Kind.SERVICE,
        )
        self.fields["product"].widget.queryset = self.fields["product"].queryset
        self.fields["product_price"].initial = self._product_price_initial()
        self.fields["commission_amount"].initial = self._commission_initial()
        self.fields["product_price"].disabled = True
        self.fields["commission_amount"].disabled = True

    def _selected_product(self):
        product = None
        if self.is_bound:
            product_id = self.data.get(self.add_prefix("product"))
            if product_id:
                product = self.fields["product"].queryset.filter(pk=product_id).first()
        elif self.instance and self.instance.pk and self.instance.product_id:
            product = self.instance.product
        return product

    def _product_price_initial(self):
        product = self._selected_product()
        return product.price if product else None

    def _commission_initial(self):
        product = self._selected_product()
        return product.barber_commission_percent if product else None


class ProductSaleForm(DashboardModelForm):
    product_price = forms.DecimalField(
        label="Valor total",
        widget=forms.NumberInput(attrs={"readonly": "readonly"}),
        required=False,
    )

    class Meta:
        model = Sale
        fields = [
            "product",
            "quantity",
            "product_price",
            "notes",
        ]
        labels = {
            "product": "Producto",
            "quantity": "Cantidad",
            "notes": "Observaciones",
            "product_price": "Valor total",
        }
        widgets = {
            "product": ServiceCatalogSelect(
                attrs={"class": "form-select", "data-product-selector": "true"},
            ),
            "quantity": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "step": "1",
                    "value": "1",
                },
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Observaciones del producto",
                },
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = CatalogItem.objects.filter(
            is_active=True,
            kind=CatalogItem.Kind.PRODUCT,
        )
        self.fields["product"].widget.queryset = self.fields["product"].queryset
        self.fields["product_price"].initial = self._product_price_initial()
        self.fields["product_price"].disabled = True

    def _selected_product(self):
        product = None
        if self.is_bound:
            product_id = self.data.get(self.add_prefix("product"))
            if product_id:
                product = self.fields["product"].queryset.filter(pk=product_id).first()
        elif self.instance and self.instance.pk and self.instance.product_id:
            product = self.instance.product
        return product

    def _product_price_initial(self):
        product = self._selected_product()
        return product.price if product else None


class ProductSaleEditForm(DashboardModelForm):
    product_price = forms.DecimalField(
        label="Valor total",
        widget=forms.NumberInput(attrs={"readonly": "readonly"}),
        required=False,
    )

    class Meta:
        model = Sale
        fields = [
            "product",
            "quantity",
            "product_price",
            "notes",
        ]
        labels = {
            "product": "Producto",
            "quantity": "Cantidad",
            "product_price": "Valor total",
            "notes": "Observaciones",
        }
        widgets = {
            "product": ServiceCatalogSelect(
                attrs={"class": "form-select", "data-product-selector": "true"},
            ),
            "quantity": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "step": "1",
                },
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Observaciones del producto",
                },
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = CatalogItem.objects.filter(
            is_active=True,
            kind=CatalogItem.Kind.PRODUCT,
        )
        self.fields["product"].widget.queryset = self.fields["product"].queryset
        self.fields["product_price"].initial = self._product_price_initial()
        self.fields["product_price"].disabled = True

    def _selected_product(self):
        product = None
        if self.is_bound:
            product_id = self.data.get(self.add_prefix("product"))
            if product_id:
                product = self.fields["product"].queryset.filter(pk=product_id).first()
        elif self.instance and self.instance.pk and self.instance.product_id:
            product = self.instance.product
        return product

    def _product_price_initial(self):
        product = self._selected_product()
        return product.price if product else None

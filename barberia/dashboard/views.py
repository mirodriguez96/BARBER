from datetime import date, datetime
from decimal import Decimal
from itertools import chain

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from barberia.accounts.models import User
from barberia.catalog.models import CatalogItem
from barberia.common.models import Company
from barberia.inventory.models import InventoryMovement
from barberia.operations.models import Purchase, Sale
from barberia.people.models import Client, Employee

from .forms import (
    BarberEditForm,
    BarberForm,
    CatalogItemEditForm,
    CatalogItemForm,
    ClientEditForm,
    ClientForm,
    CompanyForm,
    InventoryAdjustForm,
    ProductSaleEditForm,
    ProductSaleForm,
    PurchaseForm,
    SaleEditForm,
    SaleForm,
)


@login_required
def home(request):
    section = request.GET.get("section", "barbers")
    quick_view = request.GET.get("view", "list")
    record_type = request.GET.get("type", "colaborador")
    sale_type = request.GET.get("sale_type", "servicio")
    barber_id = request.GET.get("barber")
    client_id = request.GET.get("client")
    catalog_id = request.GET.get("catalog_item")
    inventory_action = request.GET.get("inventory_action", "adjust")
    sale_id = request.GET.get("sale")
    product_id = request.GET.get("product")
    if section not in {
        "barbers",
        "catalog",
        "sales",
        "payments",
        "inventory",
        "compras",
        "config",
    }:
        quick_view = "form"

    company = Company.objects.first()
    company_form = None
    if section == "config":
        if request.method == "POST":
            company_form = CompanyForm(request.POST, instance=company)
            if company_form.is_valid():
                company = company_form.save()
                message = (
                    "La información de la empresa se actualizó correctamente."
                    if company.pk
                    else "La información de la empresa se guardó correctamente."
                )
                messages.success(request, message)
                return redirect(f"{request.path}?section=config")
        else:
            company_form = CompanyForm(instance=company)

    barber_to_edit = None
    if section == "barbers" and quick_view == "edit" and barber_id:
        barber_to_edit = get_object_or_404(Employee, pk=barber_id)

    client_to_edit = None
    if section == "barbers" and quick_view == "edit" and client_id:
        client_to_edit = get_object_or_404(Client, pk=client_id)

    catalog_item_to_edit = None
    if section == "catalog" and quick_view == "edit" and catalog_id:
        catalog_item_to_edit = get_object_or_404(CatalogItem, pk=catalog_id)

    sale_to_edit = None
    if section == "sales" and quick_view == "edit" and sale_id:
        sale_to_edit = get_object_or_404(Sale, pk=sale_id)

    forms_map = {
        "barbers": BarberForm,
        "catalog": CatalogItemForm,
    }

    purchase_form = None
    inventory_adjust_form = None

    if request.method == "POST":
        section = request.POST.get("section", section)
        action = request.POST.get("action", "save")
        record_type = request.POST.get("type", "colaborador")

        # --- Employee (barber) actions ---
        if (
            section == "barbers"
            and action == "deactivate"
            and request.POST.get("barber_id")
        ):
            barber = get_object_or_404(Employee, pk=request.POST.get("barber_id"))
            barber.is_active = False
            barber.save(update_fields=["is_active", "updated_at"])
            messages.success(request, f"{barber.full_name} fue desactivado.")
            return redirect(f"{request.path}?section=barbers&view=list")

        if (
            section == "barbers"
            and action == "activate"
            and request.POST.get("barber_id")
        ):
            barber = get_object_or_404(Employee, pk=request.POST.get("barber_id"))
            barber.is_active = True
            barber.save(update_fields=["is_active", "updated_at"])
            messages.success(request, f"{barber.full_name} fue activado.")
            return redirect(f"{request.path}?section=barbers&view=list")

        if (
            section == "barbers"
            and action == "update"
            and request.POST.get("barber_id")
        ):
            barber = get_object_or_404(Employee, pk=request.POST.get("barber_id"))
            form = BarberEditForm(request.POST, instance=barber)
            if form.is_valid():
                form.save()
                messages.success(request, "Colaborador actualizado correctamente.")
                return redirect(f"{request.path}?section=barbers&view=list")
            quick_view = "edit"
            barber_to_edit = barber
            messages.error(request, "Revisa los campos marcados en rojo.")
        # --- Client actions ---
        elif (
            section == "barbers"
            and action == "deactivate"
            and request.POST.get("client_id")
        ):
            client = get_object_or_404(Client, pk=request.POST.get("client_id"))
            client.is_active = False
            client.save(update_fields=["is_active", "updated_at"])
            messages.success(request, f"{client.full_name} fue desactivado.")
            return redirect(f"{request.path}?section=barbers&view=list")

        elif (
            section == "barbers"
            and action == "activate"
            and request.POST.get("client_id")
        ):
            client = get_object_or_404(Client, pk=request.POST.get("client_id"))
            client.is_active = True
            client.save(update_fields=["is_active", "updated_at"])
            messages.success(request, f"{client.full_name} fue activado.")
            return redirect(f"{request.path}?section=barbers&view=list")

        elif (
            section == "barbers"
            and action == "update"
            and request.POST.get("client_id")
        ):
            client = get_object_or_404(Client, pk=request.POST.get("client_id"))
            form = ClientEditForm(request.POST, instance=client)
            if form.is_valid():
                form.save()
                messages.success(request, "Cliente actualizado correctamente.")
                return redirect(f"{request.path}?section=barbers&view=list")
            quick_view = "edit"
            client_to_edit = client
            messages.error(request, "Revisa los campos marcados en rojo.")
        elif section == "catalog" and action == "deactivate":
            catalog_item = get_object_or_404(
                CatalogItem,
                pk=request.POST.get("catalog_item_id"),
            )
            catalog_item.is_active = False
            catalog_item.save(update_fields=["is_active"])
            messages.success(request, f"{catalog_item.name} fue desactivado.")
            return redirect(f"{request.path}?section=catalog&view=list")
        elif section == "catalog" and action == "activate":
            catalog_item = get_object_or_404(
                CatalogItem,
                pk=request.POST.get("catalog_item_id"),
            )
            catalog_item.is_active = True
            catalog_item.save(update_fields=["is_active"])
            messages.success(request, f"{catalog_item.name} fue activado.")
            return redirect(f"{request.path}?section=catalog&view=list")
        elif section == "catalog" and action == "update":
            catalog_item = get_object_or_404(
                CatalogItem,
                pk=request.POST.get("catalog_item_id"),
            )
            form = CatalogItemEditForm(request.POST, instance=catalog_item)
            if form.is_valid():
                form.save()
                messages.success(
                    request,
                    "Producto o servicio actualizado correctamente.",
                )
                return redirect(f"{request.path}?section=catalog&view=list")
            quick_view = "edit"
            catalog_item_to_edit = catalog_item
            messages.error(request, "Revisa los campos marcados en rojo.")
        elif section == "sales" and action == "update":
            sale = get_object_or_404(
                Sale,
                pk=request.POST.get("sale_id"),
            )
            if (
                request.user.role != User.Role.ADMIN
                and sale.employee.user_id != request.user.pk
            ):
                messages.error(
                    request,
                    "No tienes permiso para modificar este servicio.",
                )
                return redirect(f"{request.path}?section=sales&view=list")
            if sale.status == Sale.Status.CANCELED:
                messages.error(
                    request,
                    "No se puede modificar un servicio anulado.",
                )
                return redirect(f"{request.path}?section=sales&view=list")
            if sale.product.kind == CatalogItem.Kind.PRODUCT:
                form_class = ProductSaleEditForm
                old_quantity = sale.quantity
            else:
                form_class = SaleEditForm
                old_quantity = 0
            form = form_class(
                request.POST,
                instance=sale,
                user=request.user,
            )
            if form.is_valid():
                record = form.save(commit=False)
                record.performed_by = request.user
                if record.status == Sale.Status.SCHEDULED:
                    record.status = Sale.Status.DONE
                if record.product.kind == CatalogItem.Kind.PRODUCT:
                    record.product_price = record.product.price * record.quantity
                    try:
                        record.employee = request.user.employee
                    except Exception:
                        record.employee = None
                    quantity_diff = record.quantity - old_quantity
                    if quantity_diff != 0:
                        product = record.product
                        product.current_stock -= quantity_diff
                        product.save(update_fields=["current_stock"])
                        InventoryMovement.objects.create(
                            product=product,
                            quantity=-quantity_diff,
                            movement_type=InventoryMovement.MovementType.ADJUSTMENT,
                            unit_cost=product.price,
                            created_by=request.user,
                            reference_sale=record,
                            notes="Ajuste por modificación de venta",
                        )
                record.save()
                messages.success(request, "Servicio actualizado correctamente.")
                return redirect(f"{request.path}?section=sales&view=list")
            quick_view = "edit"
            sale_to_edit = sale
            messages.error(request, "Revisa los campos marcados en rojo.")
        elif section == "compras" and action == "save":
            form = PurchaseForm(request.POST, user=request.user)
            if form.is_valid():
                purchase = form.save(commit=False)
                purchase.created_by = request.user
                purchase.save()
                product = purchase.product
                product.current_stock += purchase.quantity
                product.save(update_fields=["current_stock"])
                InventoryMovement.objects.create(
                    product=product,
                    quantity=purchase.quantity,
                    movement_type=InventoryMovement.MovementType.PURCHASE,
                    unit_cost=purchase.unit_cost,
                    created_by=request.user,
                    notes=purchase.notes,
                )
                messages.success(request, "Compra registrada correctamente.")
                return redirect(f"{request.path}?section=compras&view=list")
            purchase_form = form
            messages.error(request, "Revisa los campos marcados en rojo.")

        elif section == "inventory" and action == "adjust":
            form = InventoryAdjustForm(request.POST, user=request.user)
            if form.is_valid():
                movement = form.save(commit=False)
                movement.movement_type = InventoryMovement.MovementType.ADJUSTMENT
                if movement.is_supply:
                    movement.quantity = -abs(movement.quantity)
                movement.created_by = request.user
                product = movement.product
                movement.unit_cost = product.price
                movement.save()
                product.current_stock += movement.quantity
                product.save(update_fields=["current_stock"])
                messages.success(request, "Ajuste de stock registrado correctamente.")
                return redirect(f"{request.path}?section=inventory&view=list")
            inventory_adjust_form = form
            messages.error(request, "Revisa los campos marcados en rojo.")

        elif section == "sales" and action == "cancel":
            cancel_sale_id = request.POST.get("sale_id")
            _filter_date = request.POST.get(
                "filter_date", request.GET.get("filter_date", "")
            )
            _filter_barber = request.POST.get(
                "filter_barber", request.GET.get("filter_barber", "")
            )
            _parts = []
            if _filter_date:
                _parts.append(f"filter_date={_filter_date}")
            if _filter_barber:
                _parts.append(f"filter_barber={_filter_barber}")
            filter_params_local = "&" + "&".join(_parts) if _parts else ""
            try:
                sale = Sale.objects.get(pk=cancel_sale_id)
            except Sale.DoesNotExist:
                messages.error(request, "Servicio no encontrado.")
                return redirect(
                    f"{request.path}?section=sales&view=list{filter_params_local}"
                )

            if request.user.role != User.Role.ADMIN:
                messages.error(request, "No tienes permiso para anular este servicio.")
                return redirect(
                    f"{request.path}?section=sales&view=list{filter_params_local}"
                )

            if sale.status == Sale.Status.CANCELED:
                messages.info(request, "El servicio ya está anulado.")
                return redirect(
                    f"{request.path}?section=sales&view=list{filter_params_local}"
                )

            sale.status = Sale.Status.CANCELED
            sale.save(update_fields=["status"])
            messages.success(request, "Servicio anulado correctamente.")
            return redirect(
                f"{request.path}?section=sales&view=list{filter_params_local}"
            )
        else:
            if section == "barbers":
                form_class = ClientForm if record_type == "cliente" else BarberForm
            elif section == "sales":
                form_class = ProductSaleForm if record_type == "producto" else SaleForm
            else:
                form_class = forms_map.get(section, BarberForm)
            form = form_class(request.POST, user=request.user)
            if form.is_valid():
                record = form.save(commit=False)
                if section == "sales":
                    record.performed_by = request.user
                    if not record.scheduled_for:
                        record.scheduled_for = timezone.now()
                    record.status = Sale.Status.DONE
                    if record_type == "producto":
                        record.product_price = record.product.price * record.quantity
                        try:
                            record.employee = request.user.employee
                        except Exception:
                            record.employee = None
                record.save()
                if section == "sales" and record_type == "producto":
                    product = record.product
                    product.current_stock -= record.quantity
                    product.save(update_fields=["current_stock"])
                    unit_price = record.product_price / record.quantity
                    InventoryMovement.objects.create(
                        product=product,
                        quantity=-record.quantity,
                        movement_type=InventoryMovement.MovementType.SALE,
                        unit_cost=unit_price,
                        created_by=request.user,
                        reference_sale=record,
                    )
                messages.success(request, "Registro guardado correctamente.")
                return redirect(f"{request.path}?section={section}")
            messages.error(request, "Revisa los campos marcados en rojo.")
    elif section == "barbers" and quick_view == "edit":
        if barber_to_edit is not None:
            form = BarberEditForm(instance=barber_to_edit)
        elif client_to_edit is not None:
            form = ClientEditForm(instance=client_to_edit)
        else:
            form = BarberForm(user=request.user)
    elif (
        section == "catalog"
        and quick_view == "edit"
        and catalog_item_to_edit is not None
    ):
        form = CatalogItemEditForm(instance=catalog_item_to_edit)
    elif section == "sales" and quick_view == "edit" and sale_to_edit is not None:
        if (
            request.user.role != User.Role.ADMIN
            and sale_to_edit.employee.user_id != request.user.pk
        ):
            messages.error(
                request,
                "No tienes permiso para modificar este servicio.",
            )
            return redirect(f"{request.path}?section=sales&view=list")
        if sale_to_edit.product.kind == CatalogItem.Kind.PRODUCT:
            form = ProductSaleEditForm(
                instance=sale_to_edit,
                user=request.user,
            )
        else:
            form = SaleEditForm(
                instance=sale_to_edit,
                user=request.user,
            )
    else:
        if section == "barbers":
            form_class = ClientForm if record_type == "cliente" else BarberForm
            form = form_class(user=request.user)
        elif section == "sales":
            form_class = ProductSaleForm if sale_type == "producto" else SaleForm
            form = form_class(user=request.user)
        elif section == "inventory":
            if inventory_action == "adjust":
                form = InventoryAdjustForm(user=request.user)
            else:
                form = None
        elif section == "compras":
            form = PurchaseForm(user=request.user)
        else:
            form_class = forms_map.get(section, BarberForm)
            form = form_class(user=request.user)

    filter_date = request.GET.get("filter_date", "")
    filter_barber = request.GET.get("filter_barber", "")
    filter_kind = request.GET.get("filter_kind", "")
    barber_search = request.GET.get("barber_search", "").strip()
    catalog_search = request.GET.get("catalog_search", "").strip()
    catalog_kind = request.GET.get("catalog_kind", "")
    purchase_filter_date = request.GET.get("purchase_filter_date", "")
    purchase_filter_product = request.GET.get("purchase_filter_product", "").strip()

    sale_list = Sale.objects.select_related(
        "client",
        "employee",
        "product",
        "performed_by",
    ).order_by("-scheduled_for")

    if request.user.role != User.Role.ADMIN:
        sale_list = sale_list.filter(employee__user=request.user)

    filtered_sale_list = sale_list
    if filter_date == "today":
        filtered_sale_list = filtered_sale_list.filter(
            scheduled_for__date=date.today(),
        )
    elif filter_date:
        try:
            parsed = datetime.strptime(filter_date, "%Y-%m-%d").date()
            filtered_sale_list = filtered_sale_list.filter(
                scheduled_for__date=parsed,
            )
        except ValueError:
            pass

    if filter_barber:
        filtered_sale_list = filtered_sale_list.filter(employee_id=filter_barber)

    if filter_kind == "service":
        filtered_sale_list = filtered_sale_list.filter(
            product__kind=CatalogItem.Kind.SERVICE,
        )
    elif filter_kind == "product":
        filtered_sale_list = filtered_sale_list.filter(
            product__kind=CatalogItem.Kind.PRODUCT,
        )

    filter_parts = []
    if filter_date:
        filter_parts.append(f"filter_date={filter_date}")
    if filter_barber:
        filter_parts.append(f"filter_barber={filter_barber}")
    if filter_kind:
        filter_parts.append(f"filter_kind={filter_kind}")
    filter_params = "&" + "&".join(filter_parts) if filter_parts else ""
    barber_filter_params = f"&barber_search={barber_search}" if barber_search else ""
    catalog_filter_params = (
        f"&catalog_search={catalog_search}" if catalog_search else ""
    )
    if catalog_kind:
        catalog_filter_params += f"&catalog_kind={catalog_kind}"

    # --- Combined people list (barbers + clients) ---
    barber_qs = Employee.objects.all()
    client_qs = Client.objects.all()
    if barber_search:
        barber_qs = barber_qs.filter(
            Q(full_name__icontains=barber_search)
            | Q(document_id__icontains=barber_search)
        )
        client_qs = client_qs.filter(
            Q(full_name__icontains=barber_search)
            | Q(document_id__icontains=barber_search)
        )

    barber_data = [
        {
            "pk": e.pk,
            "full_name": e.full_name,
            "document_id": e.document_id,
            "phone": e.phone,
            "email": e.email,
            "is_active": e.is_active,
            "created_at": e.created_at,
            "type": "colaborador",
            "type_label": "Colaborador",
        }
        for e in barber_qs
    ]
    client_data = [
        {
            "pk": c.pk,
            "full_name": c.full_name,
            "document_id": c.document_id,
            "phone": c.phone,
            "email": "",
            "is_active": c.is_active,
            "created_at": c.created_at,
            "type": "cliente",
            "type_label": "Cliente",
        }
        for c in client_qs
    ]
    combined = sorted(
        chain(barber_data, client_data),
        key=lambda x: x["created_at"],
        reverse=True,
    )
    people_paginator = Paginator(combined, 10)
    people_page_number = request.GET.get("page")
    people_page = people_paginator.get_page(people_page_number)

    catalog_list = CatalogItem.objects.order_by("-id")
    if catalog_search:
        catalog_list = catalog_list.filter(name__icontains=catalog_search)
    if catalog_kind == "product":
        catalog_list = catalog_list.filter(kind=CatalogItem.Kind.PRODUCT)
    elif catalog_kind == "service":
        catalog_list = catalog_list.filter(kind=CatalogItem.Kind.SERVICE)
    catalog_paginator = Paginator(catalog_list, 10)
    catalog_page_number = request.GET.get("page")
    catalog_items = catalog_paginator.get_page(catalog_page_number)
    service_paginator = Paginator(filtered_sale_list, 10)
    service_page_number = request.GET.get("page")
    sales = service_paginator.get_page(service_page_number)

    barber_stats = {
        "total": barber_qs.count() + client_qs.count(),
        "barbers": barber_qs.count(),
        "clients": client_qs.count(),
        "active": barber_qs.filter(is_active=True).count()
        + client_qs.filter(is_active=True).count(),
        "inactive": barber_qs.filter(is_active=False).count()
        + client_qs.filter(is_active=False).count(),
    }
    catalog_stats = {
        "total": catalog_list.count(),
        "active": catalog_list.filter(is_active=True).count(),
        "inactive": catalog_list.filter(is_active=False).count(),
        "sales": catalog_list.filter(kind=CatalogItem.Kind.SERVICE).count(),
        "products": catalog_list.filter(kind=CatalogItem.Kind.PRODUCT).count(),
    }
    sale_stats = {
        "total": sale_list.count(),
        "done": sale_list.filter(status=Sale.Status.DONE).count(),
        "scheduled": sale_list.filter(status=Sale.Status.SCHEDULED).count(),
        "sales": sale_list.filter(product__kind=CatalogItem.Kind.SERVICE).count(),
        "products": sale_list.filter(product__kind=CatalogItem.Kind.PRODUCT).count(),
    }

    payments_qs = Employee.objects.all()
    if request.user.role != User.Role.ADMIN:
        payments_qs = payments_qs.filter(user=request.user)

    payments_aggregate_filter = Q(sales__status=Sale.Status.DONE)
    if filter_date == "today":
        payments_aggregate_filter &= Q(
            sales__scheduled_for__date=date.today(),
        )
    elif filter_date:
        try:
            parsed = datetime.strptime(filter_date, "%Y-%m-%d").date()
            payments_aggregate_filter &= Q(sales__scheduled_for__date=parsed)
        except ValueError:
            pass

    if filter_barber:
        payments_aggregate_filter &= Q(sales__employee_id=filter_barber)
        payments_qs = payments_qs.filter(pk=filter_barber)

    payments_aggregate_filter &= ~Q(
        sales__product__kind=CatalogItem.Kind.PRODUCT,
    )

    commission_expression = ExpressionWrapper(
        F("sales__product_price")
        * F("sales__product__barber_commission_percent")
        / Value(100),
        output_field=DecimalField(max_digits=10, decimal_places=2),
    )

    payments_qs = payments_qs.annotate(
        cuts_count=Coalesce(
            Count("sales", filter=payments_aggregate_filter),
            Value(0),
        ),
        commission_total=Coalesce(
            Sum(commission_expression, filter=payments_aggregate_filter),
            Value(Decimal("0.00")),
        ),
        tip_total=Coalesce(
            Sum("sales__tip_amount", filter=payments_aggregate_filter),
            Value(Decimal("0.00")),
        ),
    ).order_by("full_name")

    payments_qs = payments_qs.filter(cuts_count__gt=0)

    payments_paginator = Paginator(payments_qs, 10)
    payments_page_number = request.GET.get("page")
    payments_page = payments_paginator.get_page(payments_page_number)

    service_filter = Q(status=Sale.Status.DONE)
    if filter_date == "today":
        service_filter &= Q(scheduled_for__date=date.today())
    elif filter_date:
        try:
            parsed = datetime.strptime(filter_date, "%Y-%m-%d").date()
            service_filter &= Q(scheduled_for__date=parsed)
        except ValueError:
            pass

    if filter_barber:
        service_filter &= Q(employee_id=filter_barber)

    service_filter &= ~Q(product__kind=CatalogItem.Kind.PRODUCT)

    service_qs = Sale.objects.filter(service_filter)
    if request.user.role != User.Role.ADMIN:
        service_qs = service_qs.filter(employee__user=request.user)

    commission_expr = ExpressionWrapper(
        F("product_price") * F("product__barber_commission_percent") / Value(100),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )

    aggregates = service_qs.aggregate(
        total_cuts=Coalesce(Count("pk"), Value(0)),
        total_commission=Coalesce(Sum(commission_expr), Value(Decimal("0.00"))),
        total_tips=Coalesce(Sum("tip_amount"), Value(Decimal("0.00"))),
        total_revenue=Coalesce(Sum("product_price"), Value(Decimal("0.00"))),
    )

    revenue = aggregates.get("total_revenue") or Decimal("0.00")
    commission_only = aggregates.get("total_commission") or Decimal("0.00")
    tip_total = aggregates.get("total_tips") or Decimal("0.00")
    commission_plus_tips = commission_only + tip_total
    company_net = revenue - commission_only

    payments_summary = {
        "total_cuts": int(aggregates.get("total_cuts") or 0),
        "commission_total": commission_plus_tips,
        "tip_total": tip_total,
        "revenue_total": revenue,
        "company_net": company_net,
    }

    inventory_products = CatalogItem.objects.filter(
        kind=CatalogItem.Kind.PRODUCT,
    ).order_by("name")
    inventory_stats = {
        "total": inventory_products.count(),
        "with_stock": inventory_products.filter(current_stock__gt=0).count(),
        "out_of_stock": inventory_products.filter(current_stock__lte=0).count(),
    }
    inventory_stats["total_value"] = inventory_products.aggregate(
        total=Coalesce(
            Sum(
                ExpressionWrapper(
                    F("current_stock") * F("price"),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            ),
            Value(Decimal("0.00")),
        )
    )["total"]
    inventory_paginator = Paginator(inventory_products, 10)
    inventory_page_number = request.GET.get("page")
    inventory_page = inventory_paginator.get_page(inventory_page_number)

    purchase_page = None
    purchase_stats = None
    purchase_filter_params = ""
    if section == "compras" and quick_view == "list":
        purchase_qs = (
            Purchase.objects.select_related("product", "created_by")
            .annotate(
                total_cost=ExpressionWrapper(
                    F("quantity") * F("unit_cost"),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            )
            .order_by("-created_at")
        )
        if purchase_filter_date == "today":
            purchase_qs = purchase_qs.filter(created_at__date=date.today())
        elif purchase_filter_date:
            try:
                parsed = datetime.strptime(purchase_filter_date, "%Y-%m-%d").date()
                purchase_qs = purchase_qs.filter(created_at__date=parsed)
            except ValueError:
                pass
        if purchase_filter_product:
            purchase_qs = purchase_qs.filter(
                product__name__icontains=purchase_filter_product
            )
        purchase_filter_parts = []
        if purchase_filter_date:
            purchase_filter_parts.append(f"purchase_filter_date={purchase_filter_date}")
        if purchase_filter_product:
            purchase_filter_parts.append(
                f"purchase_filter_product={purchase_filter_product}"
            )
        purchase_filter_params = (
            "&" + "&".join(purchase_filter_parts) if purchase_filter_parts else ""
        )
        purchase_page = Paginator(purchase_qs, 10).get_page(request.GET.get("page"))
        purchase_stats = {
            "total": purchase_qs.count(),
            "total_amount": purchase_qs.aggregate(
                total=Coalesce(
                    Sum(
                        ExpressionWrapper(
                            F("quantity") * F("unit_cost"),
                            output_field=DecimalField(max_digits=12, decimal_places=2),
                        )
                    ),
                    Value(Decimal("0.00")),
                )
            )["total"],
        }

    movement_product = None
    inventory_movements_page = None
    if quick_view == "history" and product_id:
        movement_product = get_object_or_404(CatalogItem, pk=product_id)
        movements_qs = (
            InventoryMovement.objects.filter(
                product=movement_product,
            )
            .select_related("created_by")
            .order_by("-created_at")
        )
        movements_paginator = Paginator(movements_qs, 10)
        movements_page_number = request.GET.get("movements_page")
        inventory_movements_page = movements_paginator.get_page(movements_page_number)

    section_titles = {
        "barbers": "Administrar colaboradores y clientes",
        "catalog": "Administrar catálogo de productos y servicios",
        "sales": "Administrar ventas y servicios realizados",
        "payments": "Administrar pagos y comisiones",
        "inventory": "Administrar inventario",
        "compras": "Administrar compras",
        "config": "Configuración de la empresa",
    }

    context = {
        "active_section": section,
        "quick_view": quick_view,
        "record_type": record_type,
        "sale_type": sale_type,
        "barber_to_edit": barber_to_edit,
        "client_to_edit": client_to_edit,
        "catalog_item_to_edit": catalog_item_to_edit,
        "sale_to_edit": sale_to_edit,
        "section_title": section_titles.get(
            section, "Registro de colaboradores y clientes"
        ),
        "form": form,
        "people_page": people_page,
        "barbers": people_page,
        "catalog_items": catalog_items,
        "sales": sales,
        "payments_page": payments_page,
        "payments_summary": payments_summary,
        "filter_params": filter_params,
        "filter_date": filter_date,
        "filter_barber": filter_barber,
        "filter_kind": filter_kind,
        "barber_search": barber_search,
        "barber_filter_params": barber_filter_params,
        "catalog_search": catalog_search,
        "catalog_kind": catalog_kind,
        "catalog_filter_params": catalog_filter_params,
        "active_barbers": Employee.objects.filter(is_active=True),
        "barber_stats": barber_stats,
        "catalog_stats": catalog_stats,
        "sale_stats": sale_stats,
        "inventory_page": inventory_page,
        "inventory_stats": inventory_stats,
        "purchase_page": purchase_page,
        "purchase_stats": purchase_stats,
        "purchase_filter_date": purchase_filter_date,
        "purchase_filter_product": purchase_filter_product,
        "purchase_filter_params": purchase_filter_params,
        "purchase_form": purchase_form,
        "inventory_adjust_form": inventory_adjust_form,
        "inventory_action": inventory_action,
        "movement_product": movement_product,
        "inventory_movements_page": inventory_movements_page,
        "company": company,
        "company_form": company_form,
        "menu_items": [
            {"key": "barbers", "label": "COLABORADORES / CLIENTES", "hint": ""},
            {"key": "catalog", "label": "PRODUCTOS Y SERVICIOS", "hint": ""},
            {"key": "sales", "label": "VENTAS", "hint": ""},
            {"key": "compras", "label": "COMPRAS", "hint": ""},
            {"key": "payments", "label": "PAGOS", "hint": ""},
            {"key": "inventory", "label": "INVENTARIO", "hint": ""},
            {"key": "config", "label": "CONFIGURACIÓN", "hint": "Empresa"},
        ],
        "is_admin": request.user.role == User.Role.ADMIN,
    }
    return render(request, "dashboard/home.html", context)

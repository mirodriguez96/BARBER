from datetime import date, datetime
from decimal import Decimal

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone

from barberia.catalog.models import CatalogItem
from barberia.common.utils import can_deactivate, can_modify, can_register
from barberia.dashboard.models import RoleCrudPermission
from barberia.inventory.models import InventoryMovement
from barberia.operations.models import Sale
from barberia.people.models import Employee

from .forms import ProductSaleEditForm, ProductSaleForm, SaleEditForm, SaleForm

APP_KEY = RoleCrudPermission.AppKey.VENTAS


def sales_process(request, context):
    can_register_ventas = can_register(request.user, APP_KEY)
    can_modify_ventas = can_modify(request.user, APP_KEY)
    can_deactivate_ventas = can_deactivate(request.user, APP_KEY)

    context.update(
        {
            "can_register_ventas": can_register_ventas,
            "can_modify_ventas": can_modify_ventas,
            "can_deactivate_ventas": can_deactivate_ventas,
        }
    )

    is_admin = request.user.role == "admin"

    if request.method == "POST":
        result = _handle_sales_post(
            request,
            context,
            can_register_ventas,
            can_modify_ventas,
            can_deactivate_ventas,
            is_admin,
        )
        if result:
            return result

    quick_view = context.get("quick_view")

    if quick_view == "list":
        _build_sales_list_context(request, context, is_admin)
    elif quick_view == "form":
        if not can_register_ventas and not is_admin:
            messages.error(request, "No tienes permiso para registrar servicios.")
            return redirect(f"{request.path}?section=sales&view=list")
        sale_type = request.GET.get("sale_type", "servicio")
        form_class = ProductSaleForm if sale_type == "producto" else SaleForm
        context["form"] = form_class(user=request.user)
    elif quick_view == "edit" and context.get("sale_to_edit"):
        sale_to_edit = context["sale_to_edit"]
        if not can_modify_ventas and not is_admin:
            messages.error(request, "No tienes permiso para modificar servicios.")
            return redirect(f"{request.path}?section=sales&view=list")
        if not is_admin and sale_to_edit.employee.user_id != request.user.pk:
            messages.error(
                request,
                "No puedes modificar un servicio de otro colaborador.",
            )
            return redirect(f"{request.path}?section=sales&view=list")
        if sale_to_edit.product.kind == CatalogItem.Kind.PRODUCT:
            context["form"] = ProductSaleEditForm(
                instance=sale_to_edit, user=request.user
            )
        else:
            context["form"] = SaleEditForm(instance=sale_to_edit, user=request.user)


def _handle_sales_post(
    request,
    context,
    can_register_ventas,
    can_modify_ventas,
    can_deactivate_ventas,
    is_admin,
):
    action = request.POST.get("action")

    if action == "update":
        return _handle_sales_update(request, context, can_modify_ventas, is_admin)
    elif action == "cancel":
        return _handle_sales_cancel(request, can_deactivate_ventas, is_admin)
    else:
        return _handle_sales_create(request, context, can_register_ventas)


def _handle_sales_update(request, context, can_modify_ventas, is_admin):
    if not can_modify_ventas:
        messages.error(
            request,
            "No tienes permiso para modificar servicios.",
        )
        return redirect(f"{request.path}?section=sales&view=list")

    sale = get_object_or_404(Sale, pk=request.POST.get("sale_id"))

    if not is_admin and sale.employee.user_id != request.user.pk:
        messages.error(
            request,
            "No puedes modificar un servicio de otro colaborador.",
        )
        return redirect(f"{request.path}?section=sales&view=list")

    if sale.status == Sale.Status.CANCELED:
        messages.error(
            request,
            "No se puede modificar un servicio anulado.",
        )
        return redirect(f"{request.path}?section=sales&view=list")

    original_quantity = sale.quantity
    original_product_id = sale.product_id

    if sale.product.kind == CatalogItem.Kind.PRODUCT:
        form_class = ProductSaleEditForm
    else:
        form_class = SaleEditForm

    form = form_class(
        request.POST,
        instance=sale,
        user=request.user,
    )

    if form.is_valid():
        record = form.save(commit=False)
        record.performed_by = request.user
        posted_status = request.POST.get("status")
        if posted_status in (Sale.Status.SCHEDULED, Sale.Status.DONE):
            record.status = posted_status
        else:
            record.status = Sale.Status.DONE

        old_is_product = (
            original_product_id
            and CatalogItem.objects.filter(
                pk=original_product_id, kind=CatalogItem.Kind.PRODUCT
            ).exists()
        )
        new_is_product = record.product.kind == CatalogItem.Kind.PRODUCT
        same_product = (
            old_is_product
            and new_is_product
            and original_product_id == record.product_id
        )

        with transaction.atomic():
            if old_is_product and not same_product:
                revert_product = sale.product
                CatalogItem.objects.filter(pk=revert_product.pk).update(
                    current_stock=F("current_stock") + original_quantity,
                )
                InventoryMovement.objects.create(
                    product=revert_product,
                    quantity=original_quantity,
                    movement_type=InventoryMovement.MovementType.ADJUSTMENT,
                    unit_cost=revert_product.price,
                    created_by=request.user,
                    origen=record.codigo,
                    notes="Ajuste por modificación de venta",
                )
            if new_is_product:
                original_unit_price = (
                    sale.product_price / original_quantity
                    if original_quantity
                    else Decimal("0")
                )
                record.product_price = original_unit_price * record.quantity
                if same_product:
                    quantity_diff = record.quantity - original_quantity
                    if quantity_diff != 0:
                        CatalogItem.objects.filter(pk=record.product_id).update(
                            current_stock=F("current_stock") - quantity_diff,
                        )
                        InventoryMovement.objects.create(
                            product=record.product,
                            quantity=-quantity_diff,
                            movement_type=InventoryMovement.MovementType.ADJUSTMENT,
                            unit_cost=record.product.price,
                            created_by=request.user,
                            origen=record.codigo,
                            notes="Ajuste por modificación de venta",
                        )
                elif not old_is_product:
                    CatalogItem.objects.filter(pk=record.product_id).update(
                        current_stock=F("current_stock") - record.quantity,
                    )
                    InventoryMovement.objects.create(
                        product=record.product,
                        quantity=-record.quantity,
                        movement_type=InventoryMovement.MovementType.ADJUSTMENT,
                        unit_cost=record.product.price,
                        created_by=request.user,
                        origen=record.codigo,
                        notes="Ajuste por modificación de venta",
                    )
            record.save()

        messages.success(request, "Servicio actualizado correctamente.")
        return redirect(f"{request.path}?section=sales&view=list")

    context["quick_view"] = "edit"
    context["sale_to_edit"] = sale
    context["form"] = form
    messages.error(request, "Revisa los campos marcados en rojo.")
    return None


def _handle_sales_cancel(request, can_deactivate_ventas, is_admin):
    cancel_sale_id = request.POST.get("sale_id")

    try:
        sale = Sale.objects.get(pk=cancel_sale_id)
    except Sale.DoesNotExist:
        messages.error(request, "Servicio no encontrado.")
        return redirect(f"{request.path}?section=sales&view=list")

    if not can_deactivate_ventas:
        messages.error(request, "No tienes permiso para anular servicios.")
        return redirect(f"{request.path}?section=sales&view=list")

    if not is_admin and sale.employee.user_id != request.user.pk:
        messages.error(
            request,
            "No puedes anular un servicio de otro colaborador.",
        )
        return redirect(f"{request.path}?section=sales&view=list")

    if sale.status == Sale.Status.CANCELED:
        messages.info(request, "El servicio ya está anulado.")
        return redirect(f"{request.path}?section=sales&view=list")

    sale.status = Sale.Status.CANCELED
    sale.save(update_fields=["status"])

    if sale.product.kind == CatalogItem.Kind.PRODUCT:
        CatalogItem.objects.filter(pk=sale.product_id).update(
            current_stock=F("current_stock") + sale.quantity,
        )
        InventoryMovement.objects.create(
            product=sale.product,
            quantity=sale.quantity,
            movement_type=InventoryMovement.MovementType.ADJUSTMENT,
            unit_cost=sale.product.price,
            created_by=request.user,
            origen=sale.codigo,
            notes="Venta anulada — reversión de stock",
        )

    messages.success(request, "Servicio anulado correctamente.")
    return redirect(f"{request.path}?section=sales&view=list")


def _handle_sales_create(request, context, can_register_ventas):
    record_type = request.POST.get("type", "")

    if not can_register_ventas:
        messages.error(
            request,
            "No tienes permiso para registrar servicios.",
        )
        return redirect(f"{request.path}?section=sales&view=list")

    form_class = ProductSaleForm if record_type == "producto" else SaleForm
    form = form_class(request.POST, user=request.user)

    if form.is_valid():
        record = form.save(commit=False)
        record.performed_by = request.user
        if not record.scheduled_for:
            record.scheduled_for = timezone.now()
        record.status = Sale.Status.DONE
        if record.product and record.product_price is None:
            record.product_price = record.product.price
        if record_type == "producto":
            record.product_price = record.product.price * record.quantity
            try:
                record.employee = request.user.employee
            except Employee.DoesNotExist:
                record.employee = None
        record.save()
        if record_type == "producto":
            record.refresh_from_db()
            CatalogItem.objects.filter(pk=record.product_id).update(
                current_stock=F("current_stock") - record.quantity,
            )
            unit_price = record.product_price / record.quantity
            InventoryMovement.objects.create(
                product=record.product,
                quantity=-record.quantity,
                movement_type=InventoryMovement.MovementType.SALE,
                unit_cost=unit_price,
                created_by=request.user,
                origen=record.codigo,
            )
        messages.success(request, "Registro guardado correctamente.")
        return redirect(f"{request.path}?section=sales")

    context["form"] = form
    messages.error(request, "Revisa los campos marcados en rojo.")
    return None


def _build_sales_list_context(request, context, is_admin):
    filter_date = request.GET.get("filter_date", "")
    filter_barber = request.GET.get("filter_barber", "")
    filter_kind = request.GET.get("filter_kind", "")

    sale_list = Sale.objects.select_related(
        "client",
        "employee",
        "product",
        "performed_by",
    ).order_by("-scheduled_for")

    if not is_admin:
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

    paginator = Paginator(filtered_sale_list, 10)
    page_number = request.GET.get("page")
    sales = paginator.get_page(page_number)

    sale_stats = {
        "total": sale_list.count(),
        "done": sale_list.filter(status=Sale.Status.DONE).count(),
        "scheduled": sale_list.filter(status=Sale.Status.SCHEDULED).count(),
        "sales": sale_list.filter(product__kind=CatalogItem.Kind.SERVICE).count(),
        "products": sale_list.filter(product__kind=CatalogItem.Kind.PRODUCT).count(),
    }

    context.update(
        {
            "sales": sales,
            "sale_stats": sale_stats,
            "filter_params": filter_params,
        }
    )

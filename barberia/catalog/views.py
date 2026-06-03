from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect

from barberia.catalog.models import CatalogItem
from barberia.common.utils import can_deactivate, can_modify, can_register
from barberia.dashboard.models import RoleCrudPermission

from .forms import CatalogItemEditForm, CatalogItemForm

APP_KEY = RoleCrudPermission.AppKey.PRODUCTOS


def catalog_process(request, context):
    can_register_productos = can_register(request.user, APP_KEY)
    can_modify_productos = can_modify(request.user, APP_KEY)
    can_deactivate_productos = can_deactivate(request.user, APP_KEY)

    context.update(
        {
            "can_register_productos": can_register_productos,
            "can_modify_productos": can_modify_productos,
            "can_deactivate_productos": can_deactivate_productos,
        }
    )

    if request.method == "POST":
        result = _handle_catalog_post(
            request, context, can_deactivate_productos, can_modify_productos
        )
        if result:
            return result

    quick_view = context.get("quick_view")

    if quick_view == "list":
        _build_catalog_list_context(request, context)
    elif quick_view == "form":
        if not can_register_productos and not request.user.is_superuser:
            messages.error(
                request, "No tienes permiso para registrar productos o servicios."
            )
            return redirect(f"{request.path}?section=catalog&view=list")
        context["form"] = CatalogItemForm(user=request.user)
    elif quick_view == "edit" and request.GET.get("catalog_item"):
        if not can_modify_productos and not request.user.is_superuser:
            messages.error(
                request, "No tienes permiso para modificar productos o servicios."
            )
            return redirect(f"{request.path}?section=catalog&view=list")
        catalog_id = request.GET.get("catalog_item")
        catalog_item = get_object_or_404(CatalogItem, pk=catalog_id)
        context["catalog_item_to_edit"] = catalog_item
        context["form"] = CatalogItemEditForm(instance=catalog_item, user=request.user)


def _handle_catalog_post(
    request, context, can_deactivate_productos, can_modify_productos
):
    action = request.POST.get("action")

    if action == "deactivate":
        if not can_deactivate_productos:
            messages.error(
                request,
                "No tienes permiso para desactivar productos o servicios.",
            )
            return redirect(f"{request.path}?section=catalog&view=list")
        catalog_item = get_object_or_404(
            CatalogItem, pk=request.POST.get("catalog_item_id")
        )
        catalog_item.is_active = False
        catalog_item.save(update_fields=["is_active"])
        messages.success(request, f"{catalog_item.name} fue desactivado.")
        return redirect(f"{request.path}?section=catalog&view=list")

    if action == "activate":
        if not can_deactivate_productos:
            messages.error(
                request,
                "No tienes permiso para activar productos o servicios.",
            )
            return redirect(f"{request.path}?section=catalog&view=list")
        catalog_item = get_object_or_404(
            CatalogItem, pk=request.POST.get("catalog_item_id")
        )
        catalog_item.is_active = True
        catalog_item.save(update_fields=["is_active"])
        messages.success(request, f"{catalog_item.name} fue activado.")
        return redirect(f"{request.path}?section=catalog&view=list")

    if action == "update":
        if not can_modify_productos:
            messages.error(
                request,
                "No tienes permiso para modificar productos o servicios.",
            )
            return redirect(f"{request.path}?section=catalog&view=list")
        catalog_item = get_object_or_404(
            CatalogItem, pk=request.POST.get("catalog_item_id")
        )
        form = CatalogItemEditForm(
            request.POST, instance=catalog_item, user=request.user
        )
        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Producto o servicio actualizado correctamente.",
            )
            return redirect(f"{request.path}?section=catalog&view=list")
        context["quick_view"] = "edit"
        context["catalog_item_to_edit"] = catalog_item
        context["form"] = form
        messages.error(request, "Revisa los campos marcados en rojo.")

    return None


def _build_catalog_list_context(request, context):
    catalog_search = request.GET.get("catalog_search", "").strip()
    catalog_kind = request.GET.get("catalog_kind", "")

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

    catalog_stats = {
        "total": catalog_list.count(),
        "active": catalog_list.filter(is_active=True).count(),
        "inactive": catalog_list.filter(is_active=False).count(),
        "sales": catalog_list.filter(kind=CatalogItem.Kind.SERVICE).count(),
        "products": catalog_list.filter(kind=CatalogItem.Kind.PRODUCT).count(),
    }

    catalog_filter_params = (
        f"&catalog_search={catalog_search}" if catalog_search else ""
    )
    if catalog_kind:
        catalog_filter_params += f"&catalog_kind={catalog_kind}"

    context.update(
        {
            "catalog_items": catalog_items,
            "catalog_stats": catalog_stats,
            "catalog_search": catalog_search,
            "catalog_kind": catalog_kind,
            "catalog_filter_params": catalog_filter_params,
        }
    )

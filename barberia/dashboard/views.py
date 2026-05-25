from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render

from barberia.people.models import Employee
from barberia.catalog.models import CatalogItem
from barberia.operations.models import ServiceRecord

from .forms import (
    BarberEditForm,
    BarberForm,
    CatalogItemEditForm,
    CatalogItemForm,
    ServiceRecordForm,
)


@login_required
def home(request):
    section = request.GET.get("section", "barbers")
    quick_view = request.GET.get("view", "form")
    barber_id = request.GET.get("barber")
    catalog_id = request.GET.get("catalog_item")
    if section not in {"barbers", "catalog"}:
        quick_view = "form"

    barber_to_edit = None
    if section == "barbers" and quick_view == "edit" and barber_id:
        barber_to_edit = get_object_or_404(Employee, pk=barber_id)

    catalog_item_to_edit = None
    if section == "catalog" and quick_view == "edit" and catalog_id:
        catalog_item_to_edit = get_object_or_404(CatalogItem, pk=catalog_id)

    forms_map = {
        "barbers": BarberForm,
        "catalog": CatalogItemForm,
        "services": ServiceRecordForm,
    }

    if request.method == "POST":
        section = request.POST.get("section", section)
        action = request.POST.get("action", "save")

        if section == "barbers" and action == "deactivate":
            barber = get_object_or_404(Employee, pk=request.POST.get("barber_id"))
            barber.is_active = False
            barber.save(update_fields=["is_active", "updated_at"])
            messages.success(request, f"{barber.full_name} fue desactivado.")
            return redirect(f"{request.path}?section=barbers&view=list")

        if section == "barbers" and action == "activate":
            barber = get_object_or_404(Employee, pk=request.POST.get("barber_id"))
            barber.is_active = True
            barber.save(update_fields=["is_active", "updated_at"])
            messages.success(request, f"{barber.full_name} fue activado.")
            return redirect(f"{request.path}?section=barbers&view=list")

        if section == "barbers" and action == "update":
            barber = get_object_or_404(Employee, pk=request.POST.get("barber_id"))
            form = BarberEditForm(request.POST, instance=barber)
            if form.is_valid():
                form.save()
                messages.success(request, "Barbero actualizado correctamente.")
                return redirect(f"{request.path}?section=barbers&view=list")
            quick_view = "edit"
            barber_to_edit = barber
            messages.error(request, "Revisa los campos marcados en rojo.")
        elif section == "catalog" and action == "deactivate":
            catalog_item = get_object_or_404(CatalogItem, pk=request.POST.get("catalog_item_id"))
            catalog_item.is_active = False
            catalog_item.save(update_fields=["is_active"])
            messages.success(request, f"{catalog_item.name} fue desactivado.")
            return redirect(f"{request.path}?section=catalog&view=list")
        elif section == "catalog" and action == "activate":
            catalog_item = get_object_or_404(CatalogItem, pk=request.POST.get("catalog_item_id"))
            catalog_item.is_active = True
            catalog_item.save(update_fields=["is_active"])
            messages.success(request, f"{catalog_item.name} fue activado.")
            return redirect(f"{request.path}?section=catalog&view=list")
        elif section == "catalog" and action == "update":
            catalog_item = get_object_or_404(CatalogItem, pk=request.POST.get("catalog_item_id"))
            form = CatalogItemEditForm(request.POST, instance=catalog_item)
            if form.is_valid():
                form.save()
                messages.success(request, "Producto o servicio actualizado correctamente.")
                return redirect(f"{request.path}?section=catalog&view=list")
            quick_view = "edit"
            catalog_item_to_edit = catalog_item
            messages.error(request, "Revisa los campos marcados en rojo.")
        else:
            form_class = forms_map.get(section, BarberForm)
            form = form_class(request.POST)
            if form.is_valid():
                record = form.save(commit=False)
                if section == "services":
                    record.performed_by = request.user
                    record.status = ServiceRecord.Status.DONE
                record.save()
                messages.success(request, "Registro guardado correctamente.")
                return redirect(f"{request.path}?section={section}")
            messages.error(request, "Revisa los campos marcados en rojo.")
    else:
        if section == "barbers" and quick_view == "edit" and barber_to_edit is not None:
            form = BarberEditForm(instance=barber_to_edit)
        elif section == "catalog" and quick_view == "edit" and catalog_item_to_edit is not None:
            form = CatalogItemEditForm(instance=catalog_item_to_edit)
        else:
            form_class = forms_map.get(section, BarberForm)
            form = form_class()

    today_records = ServiceRecord.objects.select_related(
        "client", "barber", "service", "performed_by"
    ).order_by("-scheduled_for")[:5]

    barber_list = Employee.objects.order_by("-created_at")
    barber_paginator = Paginator(barber_list, 10)
    barber_page_number = request.GET.get("page")
    barbers = barber_paginator.get_page(barber_page_number)
    catalog_list = CatalogItem.objects.order_by("-id")
    catalog_paginator = Paginator(catalog_list, 10)
    catalog_page_number = request.GET.get("page")
    catalog_items = catalog_paginator.get_page(catalog_page_number)
    barber_stats = {
        "total": barber_list.count(),
        "active": barber_list.filter(is_active=True).count(),
        "inactive": barber_list.filter(is_active=False).count(),
    }
    catalog_stats = {
        "total": catalog_list.count(),
        "active": catalog_list.filter(is_active=True).count(),
        "inactive": catalog_list.filter(is_active=False).count(),
        "services": catalog_list.filter(kind=CatalogItem.Kind.SERVICE).count(),
        "products": catalog_list.filter(kind=CatalogItem.Kind.PRODUCT).count(),
    }

    section_titles = {
        "barbers": "Administrar barberos",
        "catalog": "Administrar productos y servicios",
        "services": "Administrar cortes y servicios",
    }

    context = {
        "active_section": section,
        "quick_view": quick_view,
        "barber_to_edit": barber_to_edit,
        "catalog_item_to_edit": catalog_item_to_edit,
        "section_title": section_titles.get(section, "Registro de barberos"),
        "form": form,
        "barbers": barbers,
        "barber_page_obj": barbers,
        "catalog_items": catalog_items,
        "catalog_page_obj": catalog_items,
        "barber_stats": barber_stats,
        "catalog_stats": catalog_stats,
        "menu_items": [
            {"key": "barbers", "label": "BARBEROS", "hint": ""},
            {"key": "catalog", "label": "PRODUCTOS Y SERVICIOS", "hint": ""},
            {"key": "services", "label": "CORTES Y SERVICIOS", "hint": ""},
        ],
        "recent_records": today_records,
    }
    return render(request, "dashboard/home.html", context)

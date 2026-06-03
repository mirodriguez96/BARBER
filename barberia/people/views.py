from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect

from barberia.common.utils import can_deactivate, can_modify, can_register
from barberia.dashboard.forms import (
    BarberEditForm,
    BarberForm,
    ClientEditForm,
    ClientForm,
)
from barberia.dashboard.models import RoleCrudPermission

from .models import Client, Employee

APP_KEY = RoleCrudPermission.AppKey.PERSONAL


def people_process(request, context):
    can_register_personal = can_register(request.user, APP_KEY)
    can_modify_personal = can_modify(request.user, APP_KEY)
    can_deactivate_personal = can_deactivate(request.user, APP_KEY)

    context.update(
        {
            "can_register_personal": can_register_personal,
            "can_modify_personal": can_modify_personal,
            "can_deactivate_personal": can_deactivate_personal,
        }
    )

    if request.method == "POST":
        result = _handle_people_post(
            request, context, can_deactivate_personal, can_modify_personal
        )
        if result:
            return result

    quick_view = context.get("quick_view")

    if quick_view == "list":
        _build_people_list_context(request, context)
    elif quick_view == "edit":
        result = _handle_people_edit(request, context, can_modify_personal)
        if result:
            return result
    elif quick_view == "form":
        if not can_register_personal and not request.user.is_superuser:
            messages.error(
                request,
                "No tienes permiso para registrar nuevos colaboradores o clientes.",
            )
            return redirect(f"{request.path}?section=barbers&view=list")
        record_type = context.get("record_type", "colaborador")
        form_class = ClientForm if record_type == "cliente" else BarberForm
        context["form"] = form_class(user=request.user)


def _handle_people_post(request, context, can_deactivate_personal, can_modify_personal):
    action = request.POST.get("action")

    # --- Create (template form doesn't send action) ---
    if not action or action == "save":
        record_type = request.POST.get("type", "colaborador")
        can_register_personal = context.get("can_register_personal", False)
        if not can_register_personal and not request.user.is_superuser:
            messages.error(
                request,
                "No tienes permiso para registrar nuevos colaboradores o clientes.",
            )
            return redirect(f"{request.path}?section=barbers&view=list")
        form_class = ClientForm if record_type == "cliente" else BarberForm
        form = form_class(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Registrado correctamente.")
            return redirect(f"{request.path}?section=barbers")
        context["form"] = form
        messages.error(request, "Revisa los campos marcados en rojo.")
        return None

    # --- Employee (barber) actions ---
    if action == "deactivate" and request.POST.get("barber_id"):
        if not can_deactivate_personal:
            messages.error(request, "No tienes permiso para desactivar colaboradores.")
            return redirect(f"{request.path}?section=barbers&view=list")
        barber = get_object_or_404(Employee, pk=request.POST.get("barber_id"))
        barber.is_active = False
        barber.save(update_fields=["is_active", "updated_at"])
        messages.success(request, f"{barber.full_name} fue desactivado.")
        return redirect(f"{request.path}?section=barbers&view=list")

    if action == "activate" and request.POST.get("barber_id"):
        if not can_deactivate_personal:
            messages.error(request, "No tienes permiso para activar colaboradores.")
            return redirect(f"{request.path}?section=barbers&view=list")
        barber = get_object_or_404(Employee, pk=request.POST.get("barber_id"))
        barber.is_active = True
        barber.save(update_fields=["is_active", "updated_at"])
        messages.success(request, f"{barber.full_name} fue activado.")
        return redirect(f"{request.path}?section=barbers&view=list")

    if action == "update" and request.POST.get("barber_id"):
        if not can_modify_personal:
            messages.error(request, "No tienes permiso para modificar colaboradores.")
            return redirect(f"{request.path}?section=barbers&view=list")
        barber = get_object_or_404(Employee, pk=request.POST.get("barber_id"))
        form = BarberEditForm(request.POST, instance=barber)
        if form.is_valid():
            form.save()
            messages.success(request, "Colaborador actualizado correctamente.")
            return redirect(f"{request.path}?section=barbers&view=list")
        context["quick_view"] = "edit"
        context["barber_to_edit"] = barber
        context["form"] = form
        messages.error(request, "Revisa los campos marcados en rojo.")
        return None

    # --- Client actions ---
    if action == "deactivate" and request.POST.get("client_id"):
        if not can_deactivate_personal:
            messages.error(request, "No tienes permiso para desactivar clientes.")
            return redirect(f"{request.path}?section=barbers&view=list")
        client = get_object_or_404(Client, pk=request.POST.get("client_id"))
        client.is_active = False
        client.save(update_fields=["is_active", "updated_at"])
        messages.success(request, f"{client.full_name} fue desactivado.")
        return redirect(f"{request.path}?section=barbers&view=list")

    if action == "activate" and request.POST.get("client_id"):
        if not can_deactivate_personal:
            messages.error(request, "No tienes permiso para activar clientes.")
            return redirect(f"{request.path}?section=barbers&view=list")
        client = get_object_or_404(Client, pk=request.POST.get("client_id"))
        client.is_active = True
        client.save(update_fields=["is_active", "updated_at"])
        messages.success(request, f"{client.full_name} fue activado.")
        return redirect(f"{request.path}?section=barbers&view=list")

    if action == "update" and request.POST.get("client_id"):
        if not can_modify_personal:
            messages.error(request, "No tienes permiso para modificar clientes.")
            return redirect(f"{request.path}?section=barbers&view=list")
        client = get_object_or_404(Client, pk=request.POST.get("client_id"))
        form = ClientEditForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, "Cliente actualizado correctamente.")
            return redirect(f"{request.path}?section=barbers&view=list")
        context["quick_view"] = "edit"
        context["client_to_edit"] = client
        context["form"] = form
        messages.error(request, "Revisa los campos marcados en rojo.")
        return None

    return None


def _handle_people_edit(request, context, can_modify_personal):
    barber_id = request.GET.get("barber")
    client_id = request.GET.get("client")

    if barber_id:
        barber_to_edit = get_object_or_404(Employee, pk=barber_id)
        if not can_modify_personal and not request.user.is_superuser:
            messages.error(request, "No tienes permiso para modificar colaboradores.")
            return redirect(f"{request.path}?section=barbers&view=list")
        context["barber_to_edit"] = barber_to_edit
        context["form"] = BarberEditForm(instance=barber_to_edit)
    elif client_id:
        client_to_edit = get_object_or_404(Client, pk=client_id)
        if not can_modify_personal and not request.user.is_superuser:
            messages.error(request, "No tienes permiso para modificar clientes.")
            return redirect(f"{request.path}?section=barbers&view=list")
        context["client_to_edit"] = client_to_edit
        context["form"] = ClientEditForm(instance=client_to_edit)
    else:
        context["form"] = BarberForm(user=request.user)


def _build_people_list_context(request, context):
    barber_search = request.GET.get("barber_search", "").strip()
    barber_type = request.GET.get("barber_type", "")

    barber_qs = Employee.objects.order_by("-created_at", "-pk")
    client_qs = Client.objects.order_by("-created_at", "-pk")

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

    if barber_type == "colaborador":
        combined = barber_data
    elif barber_type == "cliente":
        combined = client_data
    else:
        combined = list(barber_data) + list(client_data)
        combined.sort(key=lambda x: (x["created_at"], x["pk"]), reverse=True)

    people_paginator = Paginator(combined, 10)
    people_page_number = request.GET.get("page")
    people_page = people_paginator.get_page(people_page_number)

    barber_filter_params = f"&barber_search={barber_search}" if barber_search else ""
    if barber_type:
        barber_filter_params += f"&barber_type={barber_type}"

    barber_stats = {
        "total": barber_qs.count() + client_qs.count(),
        "barbers": barber_qs.count(),
        "clients": client_qs.count(),
        "active": barber_qs.filter(is_active=True).count()
        + client_qs.filter(is_active=True).count(),
        "inactive": barber_qs.filter(is_active=False).count()
        + client_qs.filter(is_active=False).count(),
    }

    context.update(
        {
            "barber_search": barber_search,
            "barber_type": barber_type,
            "barber_filter_params": barber_filter_params,
            "barber_stats": barber_stats,
            "people_page": people_page,
        }
    )

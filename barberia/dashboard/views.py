from itertools import chain
from datetime import date, datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from barberia.accounts.models import User
from barberia.catalog.models import CatalogItem
from barberia.operations.models import ServiceRecord
from barberia.people.models import Client, Employee

from .forms import (
    BarberEditForm,
    BarberForm,
    CatalogItemEditForm,
    CatalogItemForm,
    ClientEditForm,
    ClientForm,
    ProductRecordEditForm,
    ProductRecordForm,
    ServiceRecordEditForm,
    ServiceRecordForm,
)


@login_required
def home(request):
    section = request.GET.get("section", "barbers")
    quick_view = request.GET.get("view", "list")
    record_type = request.GET.get("type", "colaborador")
    service_type = request.GET.get("service_type", "servicio")
    barber_id = request.GET.get("barber")
    client_id = request.GET.get("client")
    catalog_id = request.GET.get("catalog_item")
    service_id = request.GET.get("service_record")
    if section not in {"barbers", "catalog", "services", "payments"}:
        quick_view = "form"

    barber_to_edit = None
    if section == "barbers" and quick_view == "edit" and barber_id:
        barber_to_edit = get_object_or_404(Employee, pk=barber_id)

    client_to_edit = None
    if section == "barbers" and quick_view == "edit" and client_id:
        client_to_edit = get_object_or_404(Client, pk=client_id)

    catalog_item_to_edit = None
    if section == "catalog" and quick_view == "edit" and catalog_id:
        catalog_item_to_edit = get_object_or_404(CatalogItem, pk=catalog_id)

    service_record_to_edit = None
    if section == "services" and quick_view == "edit" and service_id:
        service_record_to_edit = get_object_or_404(ServiceRecord, pk=service_id)

    forms_map = {
        "barbers": BarberForm,
        "catalog": CatalogItemForm,
    }

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
        elif section == "services" and action == "update":
            service_record = get_object_or_404(
                ServiceRecord,
                pk=request.POST.get("service_record_id"),
            )
            if (
                request.user.role != User.Role.ADMIN
                and service_record.barber.user_id != request.user.pk
            ):
                messages.error(
                    request,
                    "No tienes permiso para modificar este servicio.",
                )
                return redirect(f"{request.path}?section=services&view=list")
            if service_record.status == ServiceRecord.Status.CANCELED:
                messages.error(
                    request,
                    "No se puede modificar un servicio anulado.",
                )
                return redirect(f"{request.path}?section=services&view=list")
            if service_record.service.kind == CatalogItem.Kind.PRODUCT:
                form_class = ProductRecordEditForm
            else:
                form_class = ServiceRecordEditForm
            form = form_class(
                request.POST,
                instance=service_record,
                user=request.user,
            )
            if form.is_valid():
                record = form.save(commit=False)
                record.performed_by = request.user
                if record.status == ServiceRecord.Status.SCHEDULED:
                    record.status = ServiceRecord.Status.DONE
                if record.service.kind == CatalogItem.Kind.PRODUCT:
                    record.service_price = record.service.price * record.quantity
                    try:
                        record.barber = request.user.employee
                    except Exception:
                        record.barber = None
                record.save()
                messages.success(request, "Servicio actualizado correctamente.")
                return redirect(f"{request.path}?section=services&view=list")
            quick_view = "edit"
            service_record_to_edit = service_record
            messages.error(request, "Revisa los campos marcados en rojo.")
        elif section == "services" and action == "cancel":
            service_id = request.POST.get("service_record_id")
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
                service = ServiceRecord.objects.get(pk=service_id)
            except ServiceRecord.DoesNotExist:
                messages.error(request, "Servicio no encontrado.")
                return redirect(
                    f"{request.path}?section=services&view=list{filter_params_local}"
                )

            if request.user.role != User.Role.ADMIN:
                messages.error(request, "No tienes permiso para anular este servicio.")
                return redirect(
                    f"{request.path}?section=services&view=list{filter_params_local}"
                )

            if service.status == ServiceRecord.Status.CANCELED:
                messages.info(request, "El servicio ya está anulado.")
                return redirect(
                    f"{request.path}?section=services&view=list{filter_params_local}"
                )

            service.status = ServiceRecord.Status.CANCELED
            service.save(update_fields=["status"])
            messages.success(request, "Servicio anulado correctamente.")
            return redirect(
                f"{request.path}?section=services&view=list{filter_params_local}"
            )
        else:
            if section == "barbers":
                form_class = ClientForm if record_type == "cliente" else BarberForm
            elif section == "services":
                form_class = (
                    ProductRecordForm
                    if record_type == "producto"
                    else ServiceRecordForm
                )
            else:
                form_class = forms_map.get(section, BarberForm)
            form = form_class(request.POST, user=request.user)
            if form.is_valid():
                record = form.save(commit=False)
                if section == "services":
                    record.performed_by = request.user
                    if not record.scheduled_for:
                        record.scheduled_for = timezone.now()
                    record.status = ServiceRecord.Status.DONE
                    if record_type == "producto":
                        record.service_price = record.service.price * record.quantity
                        try:
                            record.barber = request.user.employee
                        except Exception:
                            record.barber = None
                record.save()
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
    elif (
        section == "services"
        and quick_view == "edit"
        and service_record_to_edit is not None
    ):
        if (
            request.user.role != User.Role.ADMIN
            and service_record_to_edit.barber.user_id != request.user.pk
        ):
            messages.error(
                request,
                "No tienes permiso para modificar este servicio.",
            )
            return redirect(f"{request.path}?section=services&view=list")
        if service_record_to_edit.service.kind == CatalogItem.Kind.PRODUCT:
            form = ProductRecordEditForm(
                instance=service_record_to_edit,
                user=request.user,
            )
        else:
            form = ServiceRecordEditForm(
                instance=service_record_to_edit,
                user=request.user,
            )
    else:
        if section == "barbers":
            form_class = ClientForm if record_type == "cliente" else BarberForm
        elif section == "services":
            form_class = (
                ProductRecordForm if service_type == "producto" else ServiceRecordForm
            )
        else:
            form_class = forms_map.get(section, BarberForm)
        form = form_class(user=request.user)

    filter_date = request.GET.get("filter_date", "")
    filter_barber = request.GET.get("filter_barber", "")
    filter_kind = request.GET.get("filter_kind", "")

    service_list = ServiceRecord.objects.select_related(
        "client",
        "barber",
        "service",
        "performed_by",
    ).order_by("-scheduled_for")

    if request.user.role != User.Role.ADMIN:
        service_list = service_list.filter(barber__user=request.user)

    filtered_service_list = service_list
    if filter_date == "today":
        filtered_service_list = filtered_service_list.filter(
            scheduled_for__date=date.today(),
        )
    elif filter_date:
        try:
            parsed = datetime.strptime(filter_date, "%Y-%m-%d").date()
            filtered_service_list = filtered_service_list.filter(
                scheduled_for__date=parsed,
            )
        except ValueError:
            pass

    if filter_barber:
        filtered_service_list = filtered_service_list.filter(barber_id=filter_barber)

    if filter_kind == "service":
        filtered_service_list = filtered_service_list.filter(
            service__kind=CatalogItem.Kind.SERVICE,
        )
    elif filter_kind == "product":
        filtered_service_list = filtered_service_list.filter(
            service__kind=CatalogItem.Kind.PRODUCT,
        )

    filter_parts = []
    if filter_date:
        filter_parts.append(f"filter_date={filter_date}")
    if filter_barber:
        filter_parts.append(f"filter_barber={filter_barber}")
    if filter_kind:
        filter_parts.append(f"filter_kind={filter_kind}")
    filter_params = "&" + "&".join(filter_parts) if filter_parts else ""

    # --- Combined people list (barbers + clients) ---
    barber_qs = Employee.objects.all()
    client_qs = Client.objects.all()

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
    catalog_paginator = Paginator(catalog_list, 10)
    catalog_page_number = request.GET.get("page")
    catalog_items = catalog_paginator.get_page(catalog_page_number)
    service_paginator = Paginator(filtered_service_list, 10)
    service_page_number = request.GET.get("page")
    services = service_paginator.get_page(service_page_number)

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
        "services": catalog_list.filter(kind=CatalogItem.Kind.SERVICE).count(),
        "products": catalog_list.filter(kind=CatalogItem.Kind.PRODUCT).count(),
    }
    service_stats = {
        "total": service_list.count(),
        "done": service_list.filter(status=ServiceRecord.Status.DONE).count(),
        "scheduled": service_list.filter(status=ServiceRecord.Status.SCHEDULED).count(),
        "services": service_list.filter(service__kind=CatalogItem.Kind.SERVICE).count(),
        "products": service_list.filter(service__kind=CatalogItem.Kind.PRODUCT).count(),
    }

    payments_qs = Employee.objects.all()
    if request.user.role != User.Role.ADMIN:
        payments_qs = payments_qs.filter(user=request.user)

    payments_aggregate_filter = Q(service_records__status=ServiceRecord.Status.DONE)
    if filter_date == "today":
        payments_aggregate_filter &= Q(
            service_records__scheduled_for__date=date.today(),
        )
    elif filter_date:
        try:
            parsed = datetime.strptime(filter_date, "%Y-%m-%d").date()
            payments_aggregate_filter &= Q(service_records__scheduled_for__date=parsed)
        except ValueError:
            pass

    if filter_barber:
        payments_aggregate_filter &= Q(service_records__barber_id=filter_barber)
        payments_qs = payments_qs.filter(pk=filter_barber)

    payments_aggregate_filter &= ~Q(
        service_records__service__kind=CatalogItem.Kind.PRODUCT,
    )

    commission_expression = ExpressionWrapper(
        F("service_records__service_price")
        * F("service_records__service__barber_commission_percent")
        / Value(100),
        output_field=DecimalField(max_digits=10, decimal_places=2),
    )

    payments_qs = payments_qs.annotate(
        cuts_count=Coalesce(
            Count("service_records", filter=payments_aggregate_filter),
            Value(0),
        ),
        commission_total=Coalesce(
            Sum(commission_expression, filter=payments_aggregate_filter),
            Value(Decimal("0.00")),
        ),
        tip_total=Coalesce(
            Sum("service_records__tip_amount", filter=payments_aggregate_filter),
            Value(Decimal("0.00")),
        ),
    ).order_by("full_name")

    payments_qs = payments_qs.filter(cuts_count__gt=0)

    payments_paginator = Paginator(payments_qs, 10)
    payments_page_number = request.GET.get("page")
    payments_page = payments_paginator.get_page(payments_page_number)

    service_filter = Q(status=ServiceRecord.Status.DONE)
    if filter_date == "today":
        service_filter &= Q(scheduled_for__date=date.today())
    elif filter_date:
        try:
            parsed = datetime.strptime(filter_date, "%Y-%m-%d").date()
            service_filter &= Q(scheduled_for__date=parsed)
        except ValueError:
            pass

    if filter_barber:
        service_filter &= Q(barber_id=filter_barber)

    service_filter &= ~Q(service__kind=CatalogItem.Kind.PRODUCT)

    service_qs = ServiceRecord.objects.filter(service_filter)
    if request.user.role != User.Role.ADMIN:
        service_qs = service_qs.filter(barber__user=request.user)

    commission_expr = ExpressionWrapper(
        F("service_price") * F("service__barber_commission_percent") / Value(100),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )

    aggregates = service_qs.aggregate(
        total_cuts=Coalesce(Count("pk"), Value(0)),
        total_commission=Coalesce(Sum(commission_expr), Value(Decimal("0.00"))),
        total_tips=Coalesce(Sum("tip_amount"), Value(Decimal("0.00"))),
        total_revenue=Coalesce(Sum("service_price"), Value(Decimal("0.00"))),
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

    section_titles = {
        "barbers": "Administrar colaboradores y clientes",
        "catalog": "Administrar productos y servicios",
        "services": "Administrar productos y servicios",
        "payments": "Pagos — comisiones y propinas",
    }

    context = {
        "active_section": section,
        "quick_view": quick_view,
        "record_type": record_type,
        "service_type": service_type,
        "barber_to_edit": barber_to_edit,
        "client_to_edit": client_to_edit,
        "catalog_item_to_edit": catalog_item_to_edit,
        "service_record_to_edit": service_record_to_edit,
        "section_title": section_titles.get(section, "Registro de colaboradores y clientes"),
        "form": form,
        "people_page": people_page,
        "barbers": people_page,
        "catalog_items": catalog_items,
        "services": services,
        "payments_page": payments_page,
        "payments_summary": payments_summary,
        "filter_params": filter_params,
        "filter_date": filter_date,
        "filter_barber": filter_barber,
        "filter_kind": filter_kind,
        "active_barbers": Employee.objects.filter(is_active=True),
        "barber_stats": barber_stats,
        "catalog_stats": catalog_stats,
        "service_stats": service_stats,
        "menu_items": [
            {"key": "barbers", "label": "COLABORADORES / CLIENTES", "hint": ""},
            {"key": "catalog", "label": "PRODUCTOS Y SERVICIOS", "hint": ""},
            {"key": "services", "label": "PRODUCTOS / SERVICIOS", "hint": ""},
            {"key": "payments", "label": "PAGOS", "hint": ""},
        ],
        "is_admin": request.user.role == User.Role.ADMIN,
    }
    return render(request, "dashboard/home.html", context)

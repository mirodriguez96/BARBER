from datetime import date, datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render

from barberia.accounts.models import User
from barberia.catalog.models import CatalogItem
from barberia.operations.models import ServiceRecord
from barberia.people.models import Employee

from .forms import (
    BarberEditForm,
    BarberForm,
    CatalogItemEditForm,
    CatalogItemForm,
    ServiceRecordEditForm,
    ServiceRecordForm,
)


@login_required
def home(request):
    section = request.GET.get("section", "barbers")
    quick_view = request.GET.get("view", "list")
    barber_id = request.GET.get("barber")
    catalog_id = request.GET.get("catalog_item")
    service_id = request.GET.get("service_record")
    if section not in {"barbers", "catalog", "services", "payments"}:
        quick_view = "form"

    barber_to_edit = None
    if section == "barbers" and quick_view == "edit" and barber_id:
        barber_to_edit = get_object_or_404(Employee, pk=barber_id)

    catalog_item_to_edit = None
    if section == "catalog" and quick_view == "edit" and catalog_id:
        catalog_item_to_edit = get_object_or_404(CatalogItem, pk=catalog_id)

    service_record_to_edit = None
    if section == "services" and quick_view == "edit" and service_id:
        service_record_to_edit = get_object_or_404(ServiceRecord, pk=service_id)

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
            catalog_item = get_object_or_404(
                CatalogItem, pk=request.POST.get("catalog_item_id"),
            )
            catalog_item.is_active = False
            catalog_item.save(update_fields=["is_active"])
            messages.success(request, f"{catalog_item.name} fue desactivado.")
            return redirect(f"{request.path}?section=catalog&view=list")
        elif section == "catalog" and action == "activate":
            catalog_item = get_object_or_404(
                CatalogItem, pk=request.POST.get("catalog_item_id"),
            )
            catalog_item.is_active = True
            catalog_item.save(update_fields=["is_active"])
            messages.success(request, f"{catalog_item.name} fue activado.")
            return redirect(f"{request.path}?section=catalog&view=list")
        elif section == "catalog" and action == "update":
            catalog_item = get_object_or_404(
                CatalogItem, pk=request.POST.get("catalog_item_id"),
            )
            form = CatalogItemEditForm(request.POST, instance=catalog_item)
            if form.is_valid():
                form.save()
                messages.success(
                    request, "Producto o servicio actualizado correctamente.",
                )
                return redirect(f"{request.path}?section=catalog&view=list")
            quick_view = "edit"
            catalog_item_to_edit = catalog_item
            messages.error(request, "Revisa los campos marcados en rojo.")
        elif section == "services" and action == "update":
            service_record = get_object_or_404(
                ServiceRecord, pk=request.POST.get("service_record_id"),
            )
            if (
                request.user.role != User.Role.ADMIN
                and service_record.barber.user_id != request.user.pk
            ):
                messages.error(
                    request, "No tienes permiso para modificar este servicio.",
                )
                return redirect(f"{request.path}?section=services&view=list")
            if service_record.status == ServiceRecord.Status.CANCELED:
                messages.error(
                    request, "No se puede modificar un servicio anulado.",
                )
                return redirect(f"{request.path}?section=services&view=list")
            form = ServiceRecordEditForm(
                request.POST, instance=service_record, user=request.user,
            )
            if form.is_valid():
                record = form.save(commit=False)
                record.performed_by = request.user
                if record.status == ServiceRecord.Status.SCHEDULED:
                    record.status = ServiceRecord.Status.DONE
                record.save()
                messages.success(request, "Servicio actualizado correctamente.")
                return redirect(f"{request.path}?section=services&view=list")
            quick_view = "edit"
            service_record_to_edit = service_record
            messages.error(request, "Revisa los campos marcados en rojo.")
        elif section == "services" and action == "cancel":
            # Cancel a service (admin-only)
            service_id = request.POST.get("service_record_id")
            # Preserve filter params for redirects when present in the
            # POST (or GET). Build a local filter_params string so tests
            # and runtime paths that redirect from this POST never refer
            # to an undefined variable.
            _filter_date = request.POST.get("filter_date", request.GET.get("filter_date", ""))
            _filter_barber = request.POST.get("filter_barber", request.GET.get("filter_barber", ""))
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
                return redirect(f"{request.path}?section=services&view=list{filter_params_local}")

            if request.user.role != User.Role.ADMIN:
                messages.error(request, "No tienes permiso para anular este servicio.")
                return redirect(f"{request.path}?section=services&view=list{filter_params_local}")

            if service.status == ServiceRecord.Status.CANCELED:
                messages.info(request, "El servicio ya está anulado.")
                return redirect(f"{request.path}?section=services&view=list{filter_params_local}")

            service.status = ServiceRecord.Status.CANCELED
            service.save(update_fields=["status"])
            messages.success(request, "Servicio anulado correctamente.")
            return redirect(f"{request.path}?section=services&view=list{filter_params_local}")
        else:
            form_class = forms_map.get(section, BarberForm)
            form = form_class(request.POST, user=request.user)
            if form.is_valid():
                record = form.save(commit=False)
                if section == "services":
                    record.performed_by = request.user
                    record.status = ServiceRecord.Status.DONE
                record.save()
                messages.success(request, "Registro guardado correctamente.")
                return redirect(f"{request.path}?section={section}")
            messages.error(request, "Revisa los campos marcados en rojo.")
    elif section == "barbers" and quick_view == "edit" and barber_to_edit is not None:
        form = BarberEditForm(instance=barber_to_edit)
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
                request, "No tienes permiso para modificar este servicio.",
            )
            return redirect(f"{request.path}?section=services&view=list")
        form = ServiceRecordEditForm(
            instance=service_record_to_edit, user=request.user,
        )
    else:
        form_class = forms_map.get(section, BarberForm)
        form = form_class(user=request.user)

    filter_date = request.GET.get("filter_date", "")
    filter_barber = request.GET.get("filter_barber", "")

    service_list = ServiceRecord.objects.select_related(
        "client", "barber", "service", "performed_by",
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

    filter_parts = []
    if filter_date:
        filter_parts.append(f"filter_date={filter_date}")
    if filter_barber:
        filter_parts.append(f"filter_barber={filter_barber}")
    filter_params = "&" + "&".join(filter_parts) if filter_parts else ""

    barber_list = Employee.objects.order_by("-created_at")
    barber_paginator = Paginator(barber_list, 10)
    barber_page_number = request.GET.get("page")
    barbers = barber_paginator.get_page(barber_page_number)
    catalog_list = CatalogItem.objects.order_by("-id")
    catalog_paginator = Paginator(catalog_list, 10)
    catalog_page_number = request.GET.get("page")
    catalog_items = catalog_paginator.get_page(catalog_page_number)
    service_paginator = Paginator(filtered_service_list, 10)
    service_page_number = request.GET.get("page")
    services = service_paginator.get_page(service_page_number)
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
    service_stats = {
        "total": service_list.count(),
        "done": service_list.filter(status=ServiceRecord.Status.DONE).count(),
        "scheduled": service_list.filter(status=ServiceRecord.Status.SCHEDULED).count(),
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

    commission_expression = ExpressionWrapper(
        F("service_records__service_price")
        * F("service_records__service__barber_commission_percent")
        / Value(100),
        output_field=DecimalField(max_digits=10, decimal_places=2),
    )

    payments_qs = payments_qs.annotate(
        cuts_count=Coalesce(
            Count("service_records", filter=payments_aggregate_filter), Value(0),
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

    # Only include barbers that have at least one matching service record
    # (respecting the date/filter criteria above). We filter on the
    # annotated cuts_count to show only barbers with cuts.
    payments_qs = payments_qs.filter(cuts_count__gt=0)

    payments_paginator = Paginator(payments_qs, 10)
    payments_page_number = request.GET.get("page")
    payments_page = payments_paginator.get_page(payments_page_number)

    # Compute an overall payments summary (totals) matching the same
    # filter criteria used to build the per-barber payments_qs. These
    # aggregates are used to render top-level metric cards in the
    # payments section (total cuts, total commissions, company net).
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

    # Respect non-admin users: restrict to services where barber belongs to user
    service_qs = ServiceRecord.objects.filter(service_filter)
    if request.user.role != User.Role.ADMIN:
        service_qs = service_qs.filter(barber__user=request.user)

    # Commission per service: price * commission_percent / 100
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

    # Compute company net: revenue - commissions - tips
    revenue = aggregates.get("total_revenue") or Decimal("0.00")
    commission_only = aggregates.get("total_commission") or Decimal("0.00")
    tip_total = aggregates.get("total_tips") or Decimal("0.00")
    # commission_plus_tips is what we show in the "Comisión total" card
    commission_plus_tips = commission_only + tip_total

    # Company net: revenue minus commission_only. Per request, do NOT
    # subtract tips here because they are already included in the
    # commission_total metric.
    company_net = revenue - commission_only

    payments_summary = {
        "total_cuts": int(aggregates.get("total_cuts") or 0),
        # display commission + tips as requested
        "commission_total": commission_plus_tips,
        "tip_total": tip_total,
        "revenue_total": revenue,
        "company_net": company_net,
    }

    section_titles = {
        "barbers": "Administrar barberos",
        "catalog": "Administrar productos y servicios",
        "services": "Administrar cortes y servicios",
        "payments": "Pagos — comisiones y propinas",
    }

    context = {
        "active_section": section,
        "quick_view": quick_view,
        "barber_to_edit": barber_to_edit,
        "catalog_item_to_edit": catalog_item_to_edit,
        "service_record_to_edit": service_record_to_edit,
        "section_title": section_titles.get(section, "Registro de barberos"),
        "form": form,
        "barbers": barbers,
        "catalog_items": catalog_items,
        "services": services,
        "payments_page": payments_page,
        "payments_summary": payments_summary,
        "filter_params": filter_params,
        "filter_date": filter_date,
        "filter_barber": filter_barber,
        "active_barbers": Employee.objects.filter(is_active=True),
        "barber_stats": barber_stats,
        "catalog_stats": catalog_stats,
        "service_stats": service_stats,
        "menu_items": [
            {"key": "barbers", "label": "BARBEROS", "hint": ""},
            {"key": "catalog", "label": "PRODUCTOS Y SERVICIOS", "hint": ""},
            {"key": "services", "label": "CORTES Y SERVICIOS", "hint": ""},
            {"key": "payments", "label": "PAGOS", "hint": ""},
        ],
        "is_admin": request.user.role == User.Role.ADMIN,
    }
    return render(request, "dashboard/home.html", context)

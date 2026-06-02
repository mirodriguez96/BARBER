import logging
import json
import sys
from datetime import date, datetime, time as time_type, timedelta
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone

from barberia.catalog.models import CatalogItem
from barberia.common.models import Company
from barberia.operations.models import Sale
from barberia.people.models import Client, Employee

from .forms import BookingForm

logger = logging.getLogger(__name__)


def api_barbers(request, date_str):
    try:
        parsed_date = date.fromisoformat(date_str)
    except (ValueError, TypeError):
        return JsonResponse({"error": "Fecha inválida"}, status=400)

    weekday = parsed_date.weekday()
    barbers = Employee.objects.filter(is_active=True).exclude(day_off=weekday)
    data = [
        {"id": b.id, "full_name": b.full_name}
        for b in barbers
    ]
    return JsonResponse({"barbers": data})


def api_client_lookup(request):
    email = request.GET.get("email", "").strip().lower()
    if not email:
        return JsonResponse({"found": False})

    client = Client.objects.filter(email__iexact=email).first()
    if not client:
        return JsonResponse({"found": False})

    return JsonResponse(
        {
            "found": True,
            "client": {
                "full_name": client.full_name,
                "phone": client.phone,
                "email": client.email or email,
            },
        }
    )


def service_list(request):
    services = CatalogItem.objects.filter(
        kind=CatalogItem.Kind.SERVICE, is_active=True
    )
    return render(
        request,
        "booking/service_list.html",
        {"services": services, "step": 1},
    )


def api_slots(request, service_id, date_str):
    service = get_object_or_404(
        CatalogItem,
        id=service_id,
        kind=CatalogItem.Kind.SERVICE,
        is_active=True,
    )
    try:
        parsed_date = date.fromisoformat(date_str)
    except (ValueError, TypeError):
        return JsonResponse({"error": "Fecha inválida"}, status=400)

    if parsed_date < timezone.localdate():
        return JsonResponse({"slots": []})

    barber_id = request.GET.get("barber")
    barber = None
    if barber_id:
        try:
            barber = Employee.objects.get(id=barber_id, is_active=True)
        except Employee.DoesNotExist:
            pass

    if barber is not None and barber.day_off is not None and barber.day_off == parsed_date.weekday():
        return JsonResponse({"slots": []})

    slots = _generate_time_slots(service, parsed_date, barber=barber)
    return JsonResponse({
        "slots": [{"label": s[0], "value": s[1]} for s in slots]
    })


def _generate_time_slots(service, selected_date, barber=None):
    company = Company.objects.first()
    if not company:
        return []

    if barber is not None and barber.day_off is not None and barber.day_off == selected_date.weekday():
        return []

    opening = company.opening_time
    closing = company.closing_time
    duration = service.duration_minutes or 60

    existing = Sale.objects.filter(
        status__in=(Sale.Status.SCHEDULED, Sale.Status.IN_PROGRESS),
        scheduled_for__date=selected_date,
    )
    if barber:
        existing = existing.filter(employee=barber)

    occupied_ranges = []
    for sale in existing:
        start = sale.scheduled_for
        if timezone.is_aware(start):
            start = timezone.localtime(start)
        d = sale.product.duration_minutes or 60
        end = start + timedelta(minutes=d)
        occupied_ranges.append((start.time(), end.time()))

    slots = []
    current = datetime.combine(selected_date, opening)
    end_dt = datetime.combine(selected_date, closing)
    today = timezone.localdate()

    while current + timedelta(minutes=duration) <= end_dt:
        if selected_date == today:
            now = timezone.localtime(timezone.now())
            current_aware = timezone.make_aware(current, timezone.get_current_timezone())
            if current_aware <= now:
                current += timedelta(minutes=duration)
                continue

        slot_start = current.time()
        slot_end = (current + timedelta(minutes=duration)).time()

        is_occupied = False
        for occ_start, occ_end in occupied_ranges:
            if slot_start < occ_end and slot_end > occ_start:
                is_occupied = True
                break

        if not is_occupied:
            slots.append((current.strftime("%H:%M"), current.strftime("%H:%M")))

        current += timedelta(minutes=duration)

    return slots


def booking_form(request, service_id):
    service = get_object_or_404(
        CatalogItem,
        id=service_id,
        kind=CatalogItem.Kind.SERVICE,
        is_active=True,
    )

    time_slots = []
    restored_booking_data = False

    if request.method == "POST":
        form = BookingForm(request.POST)
        form.fields["time"].required = False

        selected_date_str = request.POST.get("date")
        barber_id = request.POST.get("barber")
        barber = None
        if barber_id:
            try:
                barber = Employee.objects.get(id=barber_id, is_active=True)
            except Employee.DoesNotExist:
                pass

        if selected_date_str:
            try:
                parsed_date = date.fromisoformat(selected_date_str)
                time_slots = _generate_time_slots(service, parsed_date, barber=barber)
            except (ValueError, TypeError):
                parsed_date = None

        if time_slots:
            form.fields["time"].choices = [
                ("", "Elige un horario")
            ] + time_slots
        else:
            form.fields["time"].choices = [
                ("", "No hay horarios disponibles para esta fecha")
            ]

        selected_time = request.POST.get("time", "")
        has_time = bool(selected_time and time_slots)

        if has_time:
            form.fields["time"].required = True

        if form.is_valid() and has_time:
            barber_obj = form.cleaned_data.get("barber")
            request.session["booking_data"] = {
                "service_id": service.id,
                "date": form.cleaned_data["date"].isoformat(),
                "time": selected_time,
                "full_name": form.cleaned_data["full_name"],
                "email": form.cleaned_data["email"],
                "phone": form.cleaned_data["phone"],
                "notes": form.cleaned_data.get("notes", ""),
                "barber_id": barber_obj.id if barber_obj else None,
                "barber_name": barber_obj.full_name if barber_obj else "",
            }
            return redirect("booking:booking_confirm", service_id=service.id)
    else:
        booking_data = request.session.get("booking_data")
        if booking_data and booking_data.get("service_id") == service.id:
            restored_booking_data = True
            initial = {
                "date": booking_data.get("date"),
                "time": booking_data.get("time"),
                "full_name": booking_data.get("full_name", ""),
                "email": booking_data.get("email", ""),
                "phone": booking_data.get("phone", ""),
                "notes": booking_data.get("notes", ""),
                "barber": booking_data.get("barber_id"),
            }
            form = BookingForm(initial=initial)
            form.fields["time"].required = False
            if booking_data.get("date"):
                try:
                    parsed_date = date.fromisoformat(booking_data["date"])
                    barber = None
                    barber_id = booking_data.get("barber_id")
                    if barber_id:
                        try:
                            barber = Employee.objects.get(id=barber_id, is_active=True)
                        except Employee.DoesNotExist:
                            pass
                    time_slots = _generate_time_slots(service, parsed_date, barber=barber)
                    if time_slots:
                        form.fields["time"].choices = [("", "Elige un horario")] + time_slots
                    else:
                        form.fields["time"].choices = [("", "No hay horarios disponibles para esta fecha")]
                except (ValueError, TypeError):
                    form.fields["time"].choices = [("", "Selecciona una fecha primero")]
        else:
            form = BookingForm()

        form.fields["time"].required = False
        if not restored_booking_data:
            form.fields["time"].choices = [
                ("", "Selecciona una fecha primero")
            ]

    return render(
        request,
        "booking/booking_form.html",
        {
            "form": form,
            "service": service,
            "step": 2,
            "time_slots": time_slots,
        },
    )


def booking_confirm(request, service_id):
    booking_data = request.session.get("booking_data")
    if not booking_data or booking_data.get("service_id") != service_id:
        return redirect("booking:service_list")

    service = get_object_or_404(CatalogItem, id=service_id)

    if request.method == "POST" and request.POST.get("confirm"):
        selected_date = date.fromisoformat(booking_data["date"])
        hour, minute = map(int, booking_data["time"].split(":"))
        scheduled_dt = timezone.make_aware(
            datetime.combine(selected_date, time_type(hour, minute))
        )

        email = booking_data["email"].strip().lower()
        full_name = booking_data["full_name"].strip()
        phone = booking_data["phone"].strip()

        client, _ = Client.objects.get_or_create(
            email__iexact=email,
            defaults={"email": email, "full_name": full_name, "phone": phone},
        )
        if full_name and client.full_name != full_name:
            client.full_name = full_name
        if phone:
            client.phone = phone
        if client.email != email:
            client.email = email
        client.save()

        User = get_user_model()
        staff_user = User.objects.filter(is_staff=True).first()

        sale = Sale.objects.create(
            client=client,
            product=service,
            performed_by=staff_user,
            scheduled_for=scheduled_dt,
            status=Sale.Status.SCHEDULED,
            product_price=service.price,
            notes=booking_data.get("notes", ""),
        )

        barber_id = booking_data.get("barber_id")
        if barber_id:
            try:
                sale.employee = Employee.objects.get(id=barber_id)
                sale.save(update_fields=["employee"])
            except Employee.DoesNotExist:
                pass

        _send_confirmation_email(booking_data, service, scheduled_dt)
        del request.session["booking_data"]

        return redirect("booking:booking_done", sale_id=sale.id)

    return render(
        request,
        "booking/booking_confirm.html",
        {
            "service": service,
            "date": date.fromisoformat(booking_data["date"]),
            "time": booking_data["time"],
            "full_name": booking_data["full_name"],
            "email": booking_data["email"],
            "phone": booking_data["phone"],
            "notes": booking_data.get("notes", ""),
            "data": booking_data,
            "step": 3,
        },
    )


def booking_done(request, sale_id):
    sale = get_object_or_404(Sale, id=sale_id)
    return render(
        request,
        "booking/booking_done.html",
        {"sale": sale, "service": sale.product, "step": 4},
    )


def _send_confirmation_email(booking_data, service, scheduled_dt):
    subject = "Confirmación de cita - Barbería"
    context = {
        "client_name": booking_data["full_name"],
        "service_name": service.name,
        "date": scheduled_dt.strftime("%d/%m/%Y"),
        "time": scheduled_dt.strftime("%H:%M"),
        "price": service.price,
        "barber_name": booking_data.get("barber_name", ""),
        "notes": booking_data.get("notes", ""),
    }
    html_message = render_to_string("booking/email_confirmation.html", context)
    try:
        api_key = getattr(settings, "RESEND_API_KEY", "").strip()
        use_resend = bool(api_key) and "test" not in sys.argv
        if use_resend:
            payload = json.dumps(
                {
                    "from": getattr(settings, "RESEND_FROM_EMAIL", settings.DEFAULT_FROM_EMAIL),
                    "to": [booking_data["email"]],
                    "subject": subject,
                    "html": html_message,
                }
            ).encode("utf-8")
            request = Request(
                "https://api.resend.com/emails",
                data=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "barberia-reservas/1.0",
                },
                method="POST",
            )
            try:
                with urlopen(request, timeout=15) as response:
                    if response.status >= 400:
                        raise RuntimeError(f"Resend responded with {response.status}")
            except HTTPError as e:
                body = e.read().decode("utf-8", errors="ignore")
                raise RuntimeError(f"Resend HTTP {e.code}: {body}") from e
        elif settings.DEBUG or "test" in sys.argv:
            send_mail(
                subject,
                "",
                settings.DEFAULT_FROM_EMAIL,
                [booking_data["email"]],
                html_message=html_message,
                fail_silently=False,
            )
        else:
            logger.error(
                "Confirmation email skipped: RESEND_API_KEY is not configured in production.")
    except (URLError, Exception) as e:
        logger.error("Error sending confirmation email: %s", e)

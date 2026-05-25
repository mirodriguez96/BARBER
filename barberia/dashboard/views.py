from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect
from django.shortcuts import render

from barberia.operations.models import ServiceRecord

from .forms import BarberForm, CatalogItemForm, ServiceRecordForm


@login_required
def home(request):
    section = request.GET.get("section", "barbers")

    forms_map = {
        "barbers": BarberForm,
        "catalog": CatalogItemForm,
        "services": ServiceRecordForm,
    }

    if request.method == "POST":
        section = request.POST.get("section", section)
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
        form_class = forms_map.get(section, BarberForm)
        form = form_class()

    today_records = ServiceRecord.objects.select_related(
        "client", "barber", "service", "performed_by"
    ).order_by("-scheduled_for")[:5]

    section_titles = {
        "barbers": "Registro de barberos",
        "catalog": "Registro",
        "services": "Registro",
    }

    context = {
        "active_section": section,
        "section_title": section_titles.get(section, "Registro de barberos"),
        "form": form,
        "menu_items": [
            {"key": "barbers", "label": "BARBEROS", "hint": "REGISTRO DE BARBEROS"},
            {"key": "catalog", "label": "PRODUCTOS Y SERVICIOS", "hint": "REGISTRO"},
            {"key": "services", "label": "CORTES Y SERVICIOS", "hint": "REGISTRO"},
        ],
        "recent_records": today_records,
    }
    return render(request, "dashboard/home.html", context)

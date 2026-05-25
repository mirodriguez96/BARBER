from django.contrib.auth import login
from django.shortcuts import redirect, render

from .forms import BarberUserCreationForm


def register(request):
    if request.method == "POST":
        form = BarberUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.is_staff = True
            user.save(update_fields=["is_staff"])
            login(request, user)
            return redirect("dashboard:home")
    else:
        form = BarberUserCreationForm()
    return render(request, "accounts/register.html", {"form": form})

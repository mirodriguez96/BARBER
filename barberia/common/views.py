from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView
from django.http import JsonResponse
from django.shortcuts import render


class StyledAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Usuario",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Tu usuario"},
        ),
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Tu contraseña"},
        ),
    )


class BarberiaLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = StyledAuthenticationForm
    redirect_authenticated_user = True


def custom_page_not_found(request, exception):
    return render(request, "404.html", status=404)


def custom_server_error(request):
    return render(request, "500.html", status=500)


def health(request):
    return JsonResponse({"status": "ok", "service": "barberia"})

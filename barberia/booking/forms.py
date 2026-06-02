from django import forms

from barberia.people.models import Client, Employee


class BookingForm(forms.Form):
    date = forms.DateField(
        label="Fecha",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    barber = forms.ModelChoiceField(
        queryset=Employee.objects.filter(is_active=True),
        label="Barbero",
        empty_label="Selecciona un barbero",
        widget=forms.Select(attrs={"class": "form-select"}),
        required=False,
    )
    time = forms.ChoiceField(
        label="Horario",
        required=False,
        choices=[],
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    full_name = forms.CharField(
        label="Nombre completo",
        max_length=160,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Tu nombre"}
        ),
    )
    email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "tucorreo@ejemplo.com",
            }
        ),
    )
    phone = forms.CharField(
        label="Teléfono",
        max_length=20,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Tu número de contacto"}
        ),
    )
    notes = forms.CharField(
        label="Notas (opcional)",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Algún detalle que debamos saber",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.utils import timezone

        self.fields["date"].widget.attrs["min"] = timezone.localdate().isoformat()

    def clean_phone(self):
        return self.cleaned_data["phone"].strip()

    def clean_full_name(self):
        return self.cleaned_data["full_name"].strip()

    def clean_date(self):
        selected = self.cleaned_data["date"]
        from django.utils import timezone

        if selected < timezone.localdate():
            raise forms.ValidationError("La fecha no puede ser en el pasado.")
        return selected

    def get_or_create_client(self):
        email = self.cleaned_data["email"].strip().lower()
        full_name = self.cleaned_data["full_name"].strip()
        phone = self.cleaned_data["phone"].strip()
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
        return client

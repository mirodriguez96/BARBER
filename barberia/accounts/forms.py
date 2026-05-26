from django.contrib.auth.forms import UserCreationForm

from .models import User


class BarberUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "phone", "role")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.visible_fields():
            field.field.widget.attrs.setdefault("class", "form-control")
        self.fields["username"].widget.attrs.update(
            {"placeholder": "Nombre de usuario"},
        )
        self.fields["first_name"].widget.attrs.update({"placeholder": "Ej: Carlos"})
        self.fields["last_name"].widget.attrs.update({"placeholder": "Ej: López"})
        self.fields["email"].widget.attrs.update({"placeholder": "carlos@ejemplo.com"})
        self.fields["phone"].widget.attrs.update({"placeholder": "Ej: 71234567"})
        self.fields["password1"].widget.attrs.update({"placeholder": "••••••••"})
        self.fields["password2"].widget.attrs.update(
            {"placeholder": "Repite la contraseña"},
        )
        self.fields["role"].widget.attrs.update({"class": "form-select"})

from django import forms


class DashboardModelForm(forms.ModelForm):
    def _bootstrapify_fields(self):
        for name, field in self.fields.items():
            widget = field.widget
            base_classes = widget.attrs.get("class", "")

            if isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
                widget.attrs["class"] = f"{base_classes} form-check-input".strip()
                continue

            if isinstance(widget, forms.Select):
                widget.attrs["class"] = (
                    f"{base_classes} form-select form-select-lg".strip()
                )
            else:
                widget.attrs["class"] = (
                    f"{base_classes} form-control form-control-lg".strip()
                )

            widget.attrs.setdefault("autocomplete", "off")
            widget.attrs.setdefault("spellcheck", "false")

            if name in {"notes", "description"}:
                widget.attrs["class"] = (
                    f"{widget.attrs['class']} dashboard-textarea".strip()
                )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self._bootstrapify_fields()

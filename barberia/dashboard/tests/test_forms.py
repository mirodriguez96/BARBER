from django import forms
from django.test import TestCase

from barberia.catalog.models import CatalogItem
from barberia.dashboard.forms import DashboardModelForm


class _CatalogDashboardForm(DashboardModelForm):
    class Meta:
        model = CatalogItem
        fields = ["name", "kind", "price", "description"]


class DashboardModelFormTest(TestCase):
    def test_bootstrapify_checkbox(self):
        form = _CatalogDashboardForm()
        form.fields["extra"] = forms.BooleanField(widget=forms.CheckboxInput())
        form._bootstrapify_fields()
        field = form.fields["extra"]
        self.assertIn("form-check-input", field.widget.attrs.get("class", ""))

    def test_bootstrapify_select(self):
        form = _CatalogDashboardForm()
        self.assertIn("form-select", form.fields["kind"].widget.attrs.get("class", ""))

    def test_bootstrapify_text_input(self):
        form = _CatalogDashboardForm()
        self.assertIn("form-control", form.fields["name"].widget.attrs.get("class", ""))

    def test_bootstrapify_textarea(self):
        form = _CatalogDashboardForm()
        self.assertIn(
            "form-control", form.fields["description"].widget.attrs.get("class", ""),
        )

    def test_autocomplete_off_set(self):
        form = _CatalogDashboardForm()
        self.assertEqual(form.fields["name"].widget.attrs.get("autocomplete"), "off")

    def test_spellcheck_false_set(self):
        form = _CatalogDashboardForm()
        self.assertEqual(form.fields["name"].widget.attrs.get("spellcheck"), "false")

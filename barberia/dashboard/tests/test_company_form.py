"""Tests for ``CompanyForm`` logo upload/clear widget configuration."""

from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from barberia.dashboard.forms import CompanyForm


def _png_file(name="tenant_logo.png", size=32):
    try:
        from PIL import Image
    except ImportError:  # pragma: no cover
        return SimpleUploadedFile(name, b"", content_type="image/png")
    buf = BytesIO()
    Image.new("RGB", (size, size), color="blue").save(buf, format="PNG")
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type="image/png")


class CompanyFormLogoFieldTest(TestCase):
    def test_logo_field_is_present(self):
        form = CompanyForm()
        self.assertIn("logo", form.fields)

    def test_logo_widget_is_clearable_file_input(self):
        form = CompanyForm()
        from django import forms

        self.assertIsInstance(form.fields["logo"].widget, forms.ClearableFileInput)

    def test_logo_widget_accepts_only_images(self):
        form = CompanyForm()
        self.assertEqual(form.fields["logo"].widget.attrs.get("accept"), "image/*")

    def test_logo_field_is_optional(self):
        form = CompanyForm()
        self.assertFalse(form.fields["logo"].required)


class CompanyFormSaveLogoTest(TestCase):
    def test_form_saves_logo(self):
        data = {"nit": "900999111-1", "name": "Barbería Test"}
        files = {"logo": _png_file()}
        form = CompanyForm(data=data, files=files)
        self.assertTrue(form.is_valid(), msg=form.errors)
        company = form.save()
        self.addCleanup(company.logo.delete, save=False)
        self.assertTrue(company.logo)
        self.assertTrue(company.logo.name.startswith("logos/"))

    def test_form_valid_without_logo(self):
        data = {"nit": "900999111-2", "name": "Sin logo"}
        form = CompanyForm(data=data, files={})
        self.assertTrue(form.is_valid(), msg=form.errors)
        company = form.save()
        self.assertFalse(bool(company.logo))

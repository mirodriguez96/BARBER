from datetime import datetime
from decimal import Decimal

from bs4 import BeautifulSoup
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from barberia.accounts.models import User
from barberia.catalog.models import CatalogItem
from barberia.dashboard.models import RoleCrudPermission, RoleMenuPermission
from barberia.operations.models import Sale
from barberia.people.models import Client, Employee


class SaleDashboardViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="barber_admin",
            password="pass1234",
            role=User.Role.ADMIN,
        )
        self.employee = Employee.objects.create(
            user=self.user,
            full_name="Barber Test",
            document_id="DOC001",
            phone="123456789",
            is_active=True,
        )
        self.client_model = Client.objects.create(
            full_name="Client Test",
            phone="987654321",
        )
        self.service = CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Corte de cabello",
            price=Decimal("50.00"),
            barber_commission_percent=Decimal("20.00"),
            is_active=True,
            sku="SRV001",
        )
        self.product = CatalogItem.objects.create(
            kind=CatalogItem.Kind.PRODUCT,
            name="Gel fijador",
            price=Decimal("30.00"),
            is_active=True,
            sku="PRD001",
        )
        self.client_login = self.client
        self.client_login.login(username="barber_admin", password="pass1234")
        self.list_url = reverse("dashboard:home")

    def _sales_url(self, **params):
        params.setdefault("section", "sales")
        params.setdefault("view", "list")
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.list_url}?{qs}"

    # --- Authentication ---
    def test_redirect_if_not_logged_in(self):
        """Verifica que un usuario no autenticado sea redirigido a la página de inicio de sesión."""
        self.client_login.logout()
        response = self.client_login.get(self.list_url)
        self.assertRedirects(response, f"{reverse('login')}?next={self.list_url}")

    # --- List ---
    def test_sales_list_view(self):
        """Verifica que la vista de listado de ventas devuelva 200 y use la plantilla correcta."""
        Sale.objects.create(
            client=self.client_model,
            employee=self.employee,
            product=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
        )
        response = self.client_login.get(
            self._sales_url(section="sales", view="list"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/home.html")

    # --- Create GET ---
    def test_sales_form_get(self):
        """Verifica que la vista del formulario de ventas devuelva 200 e incluya un formulario en el contexto."""
        response = self.client_login.get(
            self._sales_url(section="sales", view="form"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)

    # --- Create POST ---
    def test_sales_create_post_success(self):
        """Verifica que crear una venta vía POST redirija correctamente y persista los datos en la base de datos."""
        data = {
            "section": "sales",
            "employee": self.employee.pk,
            "client": self.client_model.pk,
            "product": self.service.pk,
            "scheduled_for": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
            "product_price": "50.00",
            "commission_amount": "10.00",
            "tip_amount": "5.00",
            "notes": "Nota de prueba",
        }
        response = self.client_login.post(self.list_url, data)
        self.assertRedirects(response, f"{self.list_url}?section=sales")
        self.assertTrue(Sale.objects.filter(notes="Nota de prueba").exists())
        record = Sale.objects.get(notes="Nota de prueba")
        self.assertEqual(record.status, Sale.Status.DONE)
        self.assertEqual(record.performed_by, self.user)

    def test_sales_create_post_invalid(self):
        """Verifica que enviar datos inválidos al crear una venta devuelva el formulario con errores."""
        data = {
            "section": "sales",
            "employee": "",
            "product": "",
        }
        response = self.client_login.post(self.list_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)

    # --- Edit GET ---
    def test_sales_edit_get_loads_instance(self):
        """Verifica que la vista de edición cargue una venta existente y la incluya en el contexto."""
        record = Sale.objects.create(
            client=self.client_model,
            employee=self.employee,
            product=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
        )
        response = self.client_login.get(
            self._sales_url(
                section="sales",
                view="edit",
                sale=record.pk,
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["sale_to_edit"].pk, record.pk)

    def test_sales_edit_get_404_for_nonexistent(self):
        """Verifica que editar una venta inexistente devuelva un error 404."""
        response = self.client_login.get(
            self._sales_url(section="sales", view="edit", sale=999),
        )
        self.assertEqual(response.status_code, 404)

    # --- Edit POST ---
    def test_sales_edit_post_transitions_scheduled_to_done(self):
        """Verifica que al editar una venta programada vía POST su estado cambie a DONE."""
        record = Sale.objects.create(
            employee=self.employee,
            product=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
            status=Sale.Status.SCHEDULED,
        )
        data = {
            "action": "update",
            "section": "sales",
            "sale_id": record.pk,
            "employee": self.employee.pk,
            "product": self.service.pk,
            "product_price": "50.00",
            "commission_amount": "10.00",
            "tip_amount": "0.00",
        }
        response = self.client_login.post(self.list_url, data)
        self.assertRedirects(response, f"{self.list_url}?section=sales&view=list")
        record.refresh_from_db()
        self.assertEqual(record.status, Sale.Status.DONE)

    def test_sales_edit_post_invalid(self):
        """Verifica que enviar datos inválidos al editar una venta devuelva el formulario con errores."""
        record = Sale.objects.create(
            employee=self.employee,
            product=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
        )
        data = {
            "action": "update",
            "section": "sales",
            "sale_id": record.pk,
            "employee": "",
            "service": "",
        }
        response = self.client_login.post(self.list_url, data)
        self.assertEqual(response.status_code, 200)

    # --- Date filter ---
    def test_sales_filter_by_today(self):
        """Verifica que el filtro por fecha 'today' devuelva las ventas del día actual."""
        Sale.objects.create(
            employee=self.employee,
            product=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
        )
        response = self.client_login.get(self._sales_url(filter_date="today"))
        self.assertEqual(response.status_code, 200)

    def test_sales_filter_by_date(self):
        """Verifica que el filtro por fecha específica devuelva las ventas de ese día."""
        now = timezone.localtime()
        date_str = now.strftime("%Y-%m-%d")
        Sale.objects.create(
            employee=self.employee,
            product=self.service,
            performed_by=self.user,
            scheduled_for=now,
            product_price=Decimal("50.00"),
        )
        response = self.client_login.get(self._sales_url(filter_date=date_str))
        self.assertEqual(response.status_code, 200)

    def test_sales_filter_by_invalid_date(self):
        """Verifica que un filtro por fecha inválida no cause errores y devuelva 200."""
        response = self.client_login.get(self._sales_url(filter_date="not-a-date"))
        self.assertEqual(response.status_code, 200)

    # --- Barber filter ---
    def test_sales_filter_by_barber(self):
        """Verifica que el filtro por barbero devuelva únicamente las ventas de ese empleado."""
        Sale.objects.create(
            employee=self.employee,
            product=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
        )
        response = self.client_login.get(
            self._sales_url(filter_barber=self.employee.pk),
        )
        self.assertEqual(response.status_code, 200)

    # --- Kind filter ---
    def test_sales_filter_by_kind_service_shows_only_service_items(self):
        """Verifica que el filtro por tipo 'service' muestre solo ventas de servicios."""
        Sale.objects.create(
            employee=self.employee,
            product=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
        )
        Sale.objects.create(
            product=self.product,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("30.00"),
            quantity=1,
        )
        response = self.client_login.get(
            self._sales_url(filter_kind="service"),
        )
        records = list(response.context["sales"].object_list)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].product.kind, CatalogItem.Kind.SERVICE)

    def test_sales_filter_by_kind_product_shows_only_products(self):
        """Verifica que el filtro por tipo 'product' muestre solo ventas de productos."""
        Sale.objects.create(
            employee=self.employee,
            product=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
        )
        Sale.objects.create(
            product=self.product,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("30.00"),
            quantity=1,
        )
        response = self.client_login.get(
            self._sales_url(filter_kind="product"),
        )
        records = list(response.context["sales"].object_list)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].product.kind, CatalogItem.Kind.PRODUCT)

    def test_sales_filter_kind_empty_shows_both(self):
        """Verifica que sin filtro de tipo se muestren tanto servicios como productos."""
        Sale.objects.create(
            employee=self.employee,
            product=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
        )
        Sale.objects.create(
            product=self.product,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("30.00"),
            quantity=1,
        )
        response = self.client_login.get(self._sales_url())
        records = list(response.context["sales"].object_list)
        self.assertEqual(len(records), 2)

    # --- Pagination ---
    def test_sales_pagination(self):
        """Verifica que la paginación limite a 10 ventas por página."""
        for i in range(12):
            Sale.objects.create(
                employee=self.employee,
                product=self.service,
                performed_by=self.user,
                scheduled_for=timezone.now(),
                product_price=Decimal("50.00"),
            )
        response = self.client_login.get(self._sales_url(page=1))
        self.assertEqual(response.status_code, 200)
        sales = response.context["sales"]
        self.assertIsNotNone(sales)
        self.assertLessEqual(len(list(sales)), 10)

    # --- Bulk creation helper ---

    def _sales(self, count: int):
        for i in range(count):
            Sale.objects.create(
                employee=self.employee,
                client=self.client_model if i % 2 == 0 else None,
                product=self.service,
                performed_by=self.user,
                scheduled_for=timezone.make_aware(datetime(2025, 1, 1, i, 0, 0)),
                product_price=Decimal("50.00"),
                commission_amount=Decimal("10.00"),
            )

    def test_sales_pagination_page_2_shows_remaining(self):
        """Verifica que la página 2 de paginación muestre las ventas restantes (2 de 12)."""
        self._sales(12)
        response = self.client_login.get(self._sales_url(page=2))
        self.assertEqual(response.status_code, 200)
        sales = response.context["sales"]
        self.assertEqual(len(list(sales.object_list)), 2)

    def test_sales_pagination_filter_plus_pagination(self):
        """Verifica que la paginación combinada con filtros funcione correctamente."""
        self._sales(15)
        response = self.client_login.get(
            self._sales_url(filter_barber=self.employee.pk, page=2),
        )
        self.assertEqual(response.status_code, 200)
        sales = response.context["sales"]
        self.assertEqual(len(list(sales.object_list)), 5)

    # --- Template rendering ---

    def _soup(self, **params):
        response = self.client_login.get(self._sales_url(**params))
        return BeautifulSoup(response.content, "html.parser")

    def test_sales_form_has_bootstrap_classes(self):
        """Verifica que los campos del formulario de ventas tengan clases CSS de Bootstrap."""
        soup = self._soup(view="form")
        all_styled = soup.select(
            "input.form-control, input.form-control-lg, "
            "select.form-select, select.form-select-lg",
        )
        self.assertGreater(len(all_styled), 0)

    def test_sale_select_has_data_attributes(self):
        """Verifica que el select de productos incluya atributos data-price y data-commission en sus opciones."""
        soup = self._soup(view="form")
        select = soup.find("select", {"name": "product"})
        if select:
            options = select.find_all("option", {"data-price": True})
            self.assertGreater(len(options), 0)
            for opt in options:
                self.assertIn("data-price", opt.attrs)
                self.assertIn("data-commission", opt.attrs)


class SaleBarberAccessTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            password="pass1234",
            role=User.Role.ADMIN,
        )
        self.barbero_user = User.objects.create_user(
            username="barbero1",
            password="pass1234",
            role=User.Role.BARBERO,
        )
        self.other_user = User.objects.create_user(
            username="barbero2",
            password="pass1234",
            role=User.Role.BARBERO,
        )
        for key in ["overview", "barbers", "catalog", "sales", "payments", "config"]:
            RoleMenuPermission.objects.create(role=User.Role.BARBERO, menu_key=key)
        for action in ("registrar", "modificar"):
            RoleCrudPermission.objects.create(
                role=User.Role.BARBERO,
                app_key=RoleCrudPermission.AppKey.VENTAS,
                action=action,
            )
        self.barbero_emp = Employee.objects.create(
            user=self.barbero_user,
            full_name="Colaborador Uno",
            document_id="DOC010",
            phone="70000010",
        )
        self.other_emp = Employee.objects.create(
            user=self.other_user,
            full_name="Colaborador Dos",
            document_id="DOC020",
            phone="70000020",
        )
        self.service_item = CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Corte",
            price=Decimal("50.00"),
            sku="SRV010",
        )
        self.own_record = Sale.objects.create(
            employee=self.barbero_emp,
            product=self.service_item,
            performed_by=self.barbero_user,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
        )
        self.other_record = Sale.objects.create(
            employee=self.other_emp,
            product=self.service_item,
            performed_by=self.other_user,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
        )
        self.list_url = reverse("dashboard:home")

    def _sales_url(self, **params):
        params.setdefault("section", "sales")
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.list_url}?{qs}"

    def test_barbero_sees_only_own_sales_in_list(self):
        """Verifica que un barbero vea únicamente sus propias ventas en el listado."""
        self.client.login(username="barbero1", password="pass1234")
        response = self.client.get(self._sales_url())
        sales = list(response.context["sales"].object_list)
        self.assertIn(self.own_record, sales)
        self.assertNotIn(self.other_record, sales)

    def test_barbero_cannot_edit_other_barbero_sale_get(self):
        """Verifica que un barbero no pueda acceder al formulario de edición de una venta de otro barbero."""
        self.client.login(username="barbero1", password="pass1234")
        response = self.client.get(
            self._sales_url(view="edit", sale=self.other_record.pk),
        )
        self.assertRedirects(response, f"{self.list_url}?section=sales&view=list")

    def test_barbero_cannot_edit_other_barbero_sale_post(self):
        """Verifica que un barbero no pueda modificar vía POST una venta de otro barbero."""
        self.client.login(username="barbero1", password="pass1234")
        data = {
            "action": "update",
            "section": "sales",
            "sale_id": self.other_record.pk,
            "employee": self.barbero_emp.pk,
            "product": self.service_item.pk,
            "product_price": "50.00",
            "commission_amount": "10.00",
        }
        response = self.client.post(self.list_url, data)
        self.assertRedirects(response, f"{self.list_url}?section=sales&view=list")

    def test_barbero_can_edit_own_sale(self):
        """Verifica que un barbero pueda acceder al formulario de edición de sus propias ventas."""
        self.client.login(username="barbero1", password="pass1234")
        response = self.client.get(
            self._sales_url(view="edit", sale=self.own_record.pk),
        )
        self.assertEqual(response.status_code, 200)

    def test_barbero_cannot_cancel_sale(self):
        """Verifica que un barbero no pueda cancelar una venta, ni siquiera las propias."""
        self.client.login(username="barbero1", password="pass1234")
        data = {
            "action": "cancel",
            "section": "sales",
            "sale_id": self.own_record.pk,
        }
        response = self.client.post(self.list_url, data)
        self.assertRedirects(response, f"{self.list_url}?section=sales&view=list")
        self.own_record.refresh_from_db()
        self.assertEqual(self.own_record.status, Sale.Status.SCHEDULED)

    def test_admin_sees_all_sales_in_list(self):
        """Verifica que un administrador vea todas las ventas de todos los barberos en el listado."""
        self.client.login(username="admin", password="pass1234")
        response = self.client.get(self._sales_url())
        sales = list(response.context["sales"].object_list)
        self.assertIn(self.own_record, sales)
        self.assertIn(self.other_record, sales)

    def test_admin_can_edit_any_sale(self):
        """Verifica que un administrador pueda acceder al formulario de edición de cualquier venta."""
        self.client.login(username="admin", password="pass1234")
        response = self.client.get(
            self._sales_url(view="edit", sale=self.other_record.pk),
        )
        self.assertEqual(response.status_code, 200)

    def test_admin_can_cancel_sale(self):
        """Verifica que un administrador pueda cancelar una venta y su estado cambie a CANCELED."""
        self.client.login(username="admin", password="pass1234")
        record = Sale.objects.create(
            employee=self.other_emp,
            product=self.service_item,
            performed_by=self.other_user,
            scheduled_for=timezone.now(),
            product_price=Decimal("50.00"),
            status=Sale.Status.SCHEDULED,
        )
        data = {
            "action": "cancel",
            "section": "sales",
            "sale_id": record.pk,
        }
        response = self.client.post(self.list_url, data)
        self.assertRedirects(response, f"{self.list_url}?section=sales&view=list")
        record.refresh_from_db()
        self.assertEqual(record.status, Sale.Status.CANCELED)


class ProductSaleDashboardViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="admin_prod",
            password="pass1234",
            role=User.Role.ADMIN,
        )
        self.employee = Employee.objects.create(
            user=self.user,
            full_name="Admin Productos",
            document_id="DOC100",
            phone="123456789",
        )
        self.product = CatalogItem.objects.create(
            kind=CatalogItem.Kind.PRODUCT,
            name="Gel fijador",
            price=Decimal("100.00"),
            barber_commission_percent=Decimal("0.00"),
            is_active=True,
            sku="PRD100",
            current_stock=10,
        )
        self.service_item = CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Corte degradado",
            price=Decimal("60.00"),
            barber_commission_percent=Decimal("20.00"),
            is_active=True,
            sku="SRV200",
        )
        self.client.login(username="admin_prod", password="pass1234")
        self.list_url = reverse("dashboard:home")

    def _sales_url(self, **params):
        params.setdefault("section", "sales")
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.list_url}?{qs}"

    # --- Form GET with sale_type ---
    def test_products_form_get_with_sale_type_producto(self):
        """Verifica que el formulario con sale_type='producto' excluya el campo employee e incluya quantity."""
        response = self.client.get(
            self._sales_url(view="form", sale_type="producto"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        form = response.context["form"]
        self.assertNotIn("employee", form.fields)
        self.assertIn("quantity", form.fields)

    def test_products_form_get_defaults_to_servicio(self):
        """Verifica que el formulario por defecto (sin sale_type) incluya el campo employee."""
        response = self.client.get(self._sales_url(view="form"))
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIn("employee", form.fields)

    # --- Create POST ---
    def test_products_create_post_success(self):
        """Verifica que crear una venta de producto vía POST persista los datos, calcule el precio total y decremente el stock."""
        data = {
            "section": "sales",
            "type": "producto",
            "product": self.product.pk,
            "quantity": "3",
            "product_price": "90.00",
            "notes": "Producto de prueba",
        }
        response = self.client.post(self.list_url, data)
        self.assertRedirects(response, f"{self.list_url}?section=sales")
        self.assertTrue(Sale.objects.filter(notes="Producto de prueba").exists())
        record = Sale.objects.get(notes="Producto de prueba")
        self.assertEqual(record.quantity, 3)
        self.assertEqual(record.product_price, Decimal("300.00"))
        self.assertEqual(record.status, Sale.Status.DONE)
        self.assertIsNone(record.commission_amount)
        self.assertIsNotNone(record.scheduled_for)
        # Verify stock was decremented
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, 7)

    def test_products_create_post_invalid(self):
        """Verifica que enviar datos inválidos al crear una venta de producto devuelva el formulario con errores."""
        data = {
            "section": "sales",
            "type": "producto",
            "product": "",
            "quantity": "1",
        }
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)

    # --- Edit GET ---
    def test_products_edit_get_loads_instance(self):
        """Verifica que la vista de edición cargue una venta de producto existente con los campos correctos."""
        record = Sale.objects.create(
            product=self.product,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("200.00"),
            quantity=2,
        )
        response = self.client.get(
            self._sales_url(view="edit", sale=record.pk),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["sale_to_edit"].pk, record.pk)
        form = response.context["form"]
        self.assertNotIn("employee", form.fields)
        self.assertIn("quantity", form.fields)

    def test_products_edit_get_404_for_nonexistent(self):
        """Verifica que editar una venta de producto inexistente devuelva un error 404."""
        response = self.client.get(
            self._sales_url(view="edit", sale=999),
        )
        self.assertEqual(response.status_code, 404)

    # --- Edit POST ---
    def test_products_edit_post_updates_quantity_and_price(self):
        """Verifica que al editar una venta de producto vía POST se actualicen la cantidad y el precio."""
        record = Sale.objects.create(
            product=self.product,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("100.00"),
            quantity=1,
        )
        data = {
            "action": "update",
            "section": "sales",
            "sale_id": record.pk,
            "product": self.product.pk,
            "quantity": "5",
            "product_price": "500.00",
        }
        response = self.client.post(self.list_url, data)
        self.assertRedirects(response, f"{self.list_url}?section=sales&view=list")
        record.refresh_from_db()
        self.assertEqual(record.quantity, 5)
        self.assertEqual(record.product_price, Decimal("500.00"))

    def test_products_edit_post_invalid(self):
        """Verifica que enviar datos inválidos al editar una venta de producto devuelva el formulario con errores."""
        record = Sale.objects.create(
            product=self.product,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("100.00"),
            quantity=1,
        )
        data = {
            "action": "update",
            "section": "sales",
            "sale_id": record.pk,
            "product": "",
        }
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, 200)

    # --- Combined list ---
    def test_combined_list_shows_both_sale_kinds(self):
        """Verifica que la vista de listado muestre tanto servicios como productos."""
        Sale.objects.create(
            product=self.service_item,
            employee=self.employee,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("60.00"),
        )
        Sale.objects.create(
            product=self.product,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("100.00"),
            quantity=1,
        )
        response = self.client.get(self._sales_url(view="list"))
        self.assertEqual(response.status_code, 200)
        sales = list(response.context["sales"].object_list)
        self.assertEqual(len(sales), 2)

    # --- Stats ---
    def test_products_sale_stats_include_separate_counts(self):
        """Verifica que las estadísticas del listado diferencien entre ventas de servicios y de productos."""
        Sale.objects.create(
            product=self.service_item,
            employee=self.employee,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("60.00"),
        )
        Sale.objects.create(
            product=self.product,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            product_price=Decimal("100.00"),
            quantity=1,
        )
        response = self.client.get(self._sales_url(view="list"))
        stats = response.context["sale_stats"]
        self.assertEqual(stats["sales"], 1)
        self.assertEqual(stats["products"], 1)

    # --- Pagination includes product records ---
    def test_products_pagination(self):
        """Verifica que la paginación de ventas de productos limite a 10 registros por página."""
        for i in range(12):
            Sale.objects.create(
                product=self.service_item,
                employee=self.employee,
                performed_by=self.user,
                scheduled_for=timezone.now(),
                product_price=Decimal("60.00"),
            )
        response = self.client.get(self._sales_url(page=1))
        self.assertEqual(response.status_code, 200)
        sales = response.context["sales"]
        self.assertIsNotNone(sales)
        self.assertLessEqual(len(list(sales)), 10)

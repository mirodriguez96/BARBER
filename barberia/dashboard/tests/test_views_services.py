from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from barberia.accounts.models import User
from barberia.catalog.models import CatalogItem
from barberia.operations.models import ServiceRecord
from barberia.people.models import Client, Employee


class ServiceDashboardViewsTest(TestCase):
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

    def _services_url(self, **params):
        params.setdefault("section", "services")
        params.setdefault("view", "list")
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.list_url}?{qs}"

    # --- Authentication ---
    def test_redirect_if_not_logged_in(self):
        self.client_login.logout()
        response = self.client_login.get(self.list_url)
        self.assertRedirects(response, f"{reverse('login')}?next={self.list_url}")

    # --- List ---
    def test_services_list_view(self):
        ServiceRecord.objects.create(
            client=self.client_model,
            barber=self.employee,
            service=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            service_price=Decimal("50.00"),
        )
        response = self.client_login.get(
            self._services_url(section="services", view="list"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/home.html")

    # --- Create GET ---
    def test_services_form_get(self):
        response = self.client_login.get(
            self._services_url(section="services", view="form"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)

    # --- Create POST ---
    def test_services_create_post_success(self):
        data = {
            "section": "services",
            "barber": self.employee.pk,
            "client": self.client_model.pk,
            "service": self.service.pk,
            "scheduled_for": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
            "service_price": "50.00",
            "commission_amount": "10.00",
            "tip_amount": "5.00",
            "notes": "Nota de prueba",
        }
        response = self.client_login.post(self.list_url, data)
        self.assertRedirects(response, f"{self.list_url}?section=services")
        self.assertTrue(ServiceRecord.objects.filter(notes="Nota de prueba").exists())
        record = ServiceRecord.objects.get(notes="Nota de prueba")
        self.assertEqual(record.status, ServiceRecord.Status.DONE)
        self.assertEqual(record.performed_by, self.user)

    def test_services_create_post_invalid(self):
        data = {
            "section": "services",
            "barber": "",
            "service": "",
        }
        response = self.client_login.post(self.list_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)

    # --- Edit GET ---
    def test_services_edit_get_loads_instance(self):
        record = ServiceRecord.objects.create(
            client=self.client_model,
            barber=self.employee,
            service=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            service_price=Decimal("50.00"),
        )
        response = self.client_login.get(
            self._services_url(
                section="services",
                view="edit",
                service_record=record.pk,
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["service_record_to_edit"].pk, record.pk)

    def test_services_edit_get_404_for_nonexistent(self):
        response = self.client_login.get(
            self._services_url(section="services", view="edit", service_record=999),
        )
        self.assertEqual(response.status_code, 404)

    # --- Edit POST ---
    def test_services_edit_post_transitions_scheduled_to_done(self):
        record = ServiceRecord.objects.create(
            barber=self.employee,
            service=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            service_price=Decimal("50.00"),
            status=ServiceRecord.Status.SCHEDULED,
        )
        data = {
            "action": "update",
            "section": "services",
            "service_record_id": record.pk,
            "barber": self.employee.pk,
            "service": self.service.pk,
            "service_price": "50.00",
            "commission_amount": "10.00",
            "tip_amount": "0.00",
        }
        response = self.client_login.post(self.list_url, data)
        self.assertRedirects(response, f"{self.list_url}?section=services&view=list")
        record.refresh_from_db()
        self.assertEqual(record.status, ServiceRecord.Status.DONE)

    def test_services_edit_post_invalid(self):
        record = ServiceRecord.objects.create(
            barber=self.employee,
            service=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            service_price=Decimal("50.00"),
        )
        data = {
            "action": "update",
            "section": "services",
            "service_record_id": record.pk,
            "barber": "",
            "service": "",
        }
        response = self.client_login.post(self.list_url, data)
        self.assertEqual(response.status_code, 200)

    # --- Date filter ---
    def test_services_filter_by_today(self):
        ServiceRecord.objects.create(
            barber=self.employee,
            service=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            service_price=Decimal("50.00"),
        )
        response = self.client_login.get(self._services_url(filter_date="today"))
        self.assertEqual(response.status_code, 200)

    def test_services_filter_by_date(self):
        now = timezone.localtime()
        date_str = now.strftime("%Y-%m-%d")
        ServiceRecord.objects.create(
            barber=self.employee,
            service=self.service,
            performed_by=self.user,
            scheduled_for=now,
            service_price=Decimal("50.00"),
        )
        response = self.client_login.get(self._services_url(filter_date=date_str))
        self.assertEqual(response.status_code, 200)

    def test_services_filter_by_invalid_date(self):
        response = self.client_login.get(self._services_url(filter_date="not-a-date"))
        self.assertEqual(response.status_code, 200)

    # --- Barber filter ---
    def test_services_filter_by_barber(self):
        ServiceRecord.objects.create(
            barber=self.employee,
            service=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            service_price=Decimal("50.00"),
        )
        response = self.client_login.get(
            self._services_url(filter_barber=self.employee.pk),
        )
        self.assertEqual(response.status_code, 200)

    # --- Kind filter ---
    def test_services_filter_by_kind_service_shows_only_services(self):
        ServiceRecord.objects.create(
            barber=self.employee,
            service=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            service_price=Decimal("50.00"),
        )
        ServiceRecord.objects.create(
            service=self.product,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            service_price=Decimal("30.00"),
            quantity=1,
        )
        response = self.client_login.get(
            self._services_url(filter_kind="service"),
        )
        records = list(response.context["services"].object_list)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].service.kind, CatalogItem.Kind.SERVICE)

    def test_services_filter_by_kind_product_shows_only_products(self):
        ServiceRecord.objects.create(
            barber=self.employee,
            service=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            service_price=Decimal("50.00"),
        )
        ServiceRecord.objects.create(
            service=self.product,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            service_price=Decimal("30.00"),
            quantity=1,
        )
        response = self.client_login.get(
            self._services_url(filter_kind="product"),
        )
        records = list(response.context["services"].object_list)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].service.kind, CatalogItem.Kind.PRODUCT)

    def test_services_filter_kind_empty_shows_both(self):
        ServiceRecord.objects.create(
            barber=self.employee,
            service=self.service,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            service_price=Decimal("50.00"),
        )
        ServiceRecord.objects.create(
            service=self.product,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            service_price=Decimal("30.00"),
            quantity=1,
        )
        response = self.client_login.get(self._services_url())
        records = list(response.context["services"].object_list)
        self.assertEqual(len(records), 2)

    # --- Pagination ---
    def test_services_pagination(self):
        for i in range(12):
            ServiceRecord.objects.create(
                barber=self.employee,
                service=self.service,
                performed_by=self.user,
                scheduled_for=timezone.now(),
                service_price=Decimal("50.00"),
            )
        response = self.client_login.get(self._services_url(page=1))
        self.assertEqual(response.status_code, 200)
        services = response.context["services"]
        self.assertIsNotNone(services)
        self.assertLessEqual(len(list(services)), 10)


class ServiceBarberoAccessTest(TestCase):
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
        self.own_record = ServiceRecord.objects.create(
            barber=self.barbero_emp,
            service=self.service_item,
            performed_by=self.barbero_user,
            scheduled_for=timezone.now(),
            service_price=Decimal("50.00"),
        )
        self.other_record = ServiceRecord.objects.create(
            barber=self.other_emp,
            service=self.service_item,
            performed_by=self.other_user,
            scheduled_for=timezone.now(),
            service_price=Decimal("50.00"),
        )
        self.list_url = reverse("dashboard:home")

    def _services_url(self, **params):
        params.setdefault("section", "services")
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.list_url}?{qs}"

    def test_barbero_sees_only_own_services_in_list(self):
        self.client.login(username="barbero1", password="pass1234")
        response = self.client.get(self._services_url())
        services = list(response.context["services"].object_list)
        self.assertIn(self.own_record, services)
        self.assertNotIn(self.other_record, services)

    def test_barbero_cannot_edit_other_barbero_service_get(self):
        self.client.login(username="barbero1", password="pass1234")
        response = self.client.get(
            self._services_url(view="edit", service_record=self.other_record.pk),
        )
        self.assertRedirects(response, f"{self.list_url}?section=services&view=list")

    def test_barbero_cannot_edit_other_barbero_service_post(self):
        self.client.login(username="barbero1", password="pass1234")
        data = {
            "action": "update",
            "section": "services",
            "service_record_id": self.other_record.pk,
            "barber": self.barbero_emp.pk,
            "service": self.service_item.pk,
            "service_price": "50.00",
            "commission_amount": "10.00",
        }
        response = self.client.post(self.list_url, data)
        self.assertRedirects(response, f"{self.list_url}?section=services&view=list")

    def test_barbero_can_edit_own_service(self):
        self.client.login(username="barbero1", password="pass1234")
        data = {
            "action": "update",
            "section": "services",
            "service_record_id": self.own_record.pk,
            "barber": self.barbero_emp.pk,
            "service": self.service_item.pk,
            "service_price": "50.00",
            "commission_amount": "10.00",
            "tip_amount": "5.00",
        }
        response = self.client.post(self.list_url, data)
        self.assertRedirects(response, f"{self.list_url}?section=services&view=list")
        self.own_record.refresh_from_db()
        self.assertEqual(self.own_record.tip_amount, Decimal("5.00"))

    def test_barbero_cannot_cancel_service(self):
        self.client.login(username="barbero1", password="pass1234")
        record = ServiceRecord.objects.create(
            barber=self.other_emp,
            service=self.service_item,
            performed_by=self.other_user,
            scheduled_for=timezone.now(),
            service_price=Decimal("50.00"),
            status=ServiceRecord.Status.SCHEDULED,
        )
        data = {
            "action": "cancel",
            "section": "services",
            "service_record_id": record.pk,
        }
        response = self.client.post(self.list_url, data)
        self.assertRedirects(response, f"{self.list_url}?section=services&view=list")
        record.refresh_from_db()
        self.assertNotEqual(record.status, ServiceRecord.Status.CANCELED)

    def test_admin_sees_all_services_in_list(self):
        self.client.login(username="admin", password="pass1234")
        response = self.client.get(self._services_url())
        services = list(response.context["services"].object_list)
        self.assertIn(self.own_record, services)
        self.assertIn(self.other_record, services)

    def test_admin_can_edit_any_service(self):
        self.client.login(username="admin", password="pass1234")
        data = {
            "action": "update",
            "section": "services",
            "service_record_id": self.other_record.pk,
            "barber": self.other_emp.pk,
            "service": self.service_item.pk,
            "service_price": "50.00",
            "commission_amount": "10.00",
            "tip_amount": "3.00",
        }
        response = self.client.post(self.list_url, data)
        self.assertRedirects(response, f"{self.list_url}?section=services&view=list")
        self.other_record.refresh_from_db()
        self.assertEqual(self.other_record.tip_amount, Decimal("3.00"))

    def test_admin_can_cancel_service(self):
        self.client.login(username="admin", password="pass1234")
        record = ServiceRecord.objects.create(
            barber=self.other_emp,
            service=self.service_item,
            performed_by=self.other_user,
            scheduled_for=timezone.now(),
            service_price=Decimal("50.00"),
            status=ServiceRecord.Status.SCHEDULED,
        )
        data = {
            "action": "cancel",
            "section": "services",
            "service_record_id": record.pk,
        }
        response = self.client.post(self.list_url, data)
        self.assertRedirects(response, f"{self.list_url}?section=services&view=list")
        record.refresh_from_db()
        self.assertEqual(record.status, ServiceRecord.Status.CANCELED)


class ProductRecordDashboardViewsTest(TestCase):
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

    def _services_url(self, **params):
        params.setdefault("section", "services")
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.list_url}?{qs}"

    # --- Form GET with service_type ---
    def test_products_form_get_with_service_type_producto(self):
        response = self.client.get(
            self._services_url(view="form", service_type="producto"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        form = response.context["form"]
        self.assertNotIn("barber", form.fields)
        self.assertIn("quantity", form.fields)

    def test_products_form_get_defaults_to_servicio(self):
        response = self.client.get(self._services_url(view="form"))
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIn("barber", form.fields)

    # --- Create POST ---
    def test_products_create_post_success(self):
        data = {
            "section": "services",
            "type": "producto",
            "service": self.product.pk,
            "quantity": "3",
            "service_price": "300.00",
            "notes": "Producto de prueba",
        }
        response = self.client.post(self.list_url, data)
        self.assertRedirects(response, f"{self.list_url}?section=services")
        self.assertTrue(
            ServiceRecord.objects.filter(notes="Producto de prueba").exists()
        )
        record = ServiceRecord.objects.get(notes="Producto de prueba")
        self.assertEqual(record.quantity, 3)
        self.assertEqual(record.service_price, Decimal("300.00"))
        self.assertEqual(record.status, ServiceRecord.Status.DONE)
        self.assertIsNone(record.commission_amount)
        self.assertIsNotNone(record.scheduled_for)

    def test_products_create_post_invalid(self):
        data = {
            "section": "services",
            "type": "producto",
            "service": "",
            "quantity": "1",
        }
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)

    # --- Edit GET ---
    def test_products_edit_get_loads_instance(self):
        record = ServiceRecord.objects.create(
            service=self.product,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            service_price=Decimal("200.00"),
            quantity=2,
        )
        response = self.client.get(
            self._services_url(view="edit", service_record=record.pk),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["service_record_to_edit"].pk, record.pk)
        form = response.context["form"]
        self.assertNotIn("barber", form.fields)
        self.assertIn("quantity", form.fields)

    def test_products_edit_get_404_for_nonexistent(self):
        response = self.client.get(
            self._services_url(view="edit", service_record=999),
        )
        self.assertEqual(response.status_code, 404)

    # --- Edit POST ---
    def test_products_edit_post_updates_quantity_and_price(self):
        record = ServiceRecord.objects.create(
            service=self.product,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            service_price=Decimal("100.00"),
            quantity=1,
        )
        data = {
            "action": "update",
            "section": "services",
            "service_record_id": record.pk,
            "service": self.product.pk,
            "quantity": "5",
            "service_price": "500.00",
        }
        response = self.client.post(self.list_url, data)
        self.assertRedirects(response, f"{self.list_url}?section=services&view=list")
        record.refresh_from_db()
        self.assertEqual(record.quantity, 5)
        self.assertEqual(record.service_price, Decimal("500.00"))

    def test_products_edit_post_invalid(self):
        record = ServiceRecord.objects.create(
            service=self.product,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            service_price=Decimal("100.00"),
            quantity=1,
        )
        data = {
            "action": "update",
            "section": "services",
            "service_record_id": record.pk,
            "service": "",
        }
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, 200)

    # --- Combined list ---
    def test_combined_list_shows_service_and_product_records(self):
        ServiceRecord.objects.create(
            service=self.service_item,
            barber=self.employee,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            service_price=Decimal("60.00"),
        )
        ServiceRecord.objects.create(
            service=self.product,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            service_price=Decimal("100.00"),
            quantity=1,
        )
        response = self.client.get(self._services_url(view="list"))
        self.assertEqual(response.status_code, 200)
        services = list(response.context["services"].object_list)
        self.assertEqual(len(services), 2)

    # --- Stats ---
    def test_products_service_stats_include_separate_counts(self):
        ServiceRecord.objects.create(
            service=self.service_item,
            barber=self.employee,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            service_price=Decimal("60.00"),
        )
        ServiceRecord.objects.create(
            service=self.product,
            performed_by=self.user,
            scheduled_for=timezone.now(),
            service_price=Decimal("100.00"),
            quantity=1,
        )
        response = self.client.get(self._services_url(view="list"))
        stats = response.context["service_stats"]
        self.assertEqual(stats["services"], 1)
        self.assertEqual(stats["products"], 1)

    # --- Pagination includes product records ---
    def test_products_pagination(self):
        for i in range(12):
            ServiceRecord.objects.create(
                service=self.service_item,
                barber=self.employee,
                performed_by=self.user,
                scheduled_for=timezone.now(),
                service_price=Decimal("60.00"),
            )
        response = self.client.get(self._services_url(page=1))
        self.assertEqual(response.status_code, 200)
        services = response.context["services"]
        self.assertIsNotNone(services)
        self.assertLessEqual(len(list(services)), 10)

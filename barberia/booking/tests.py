from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from barberia.catalog.models import CatalogItem
from barberia.common.models import Company
from barberia.operations.models import Sale
from barberia.people.models import Client, Employee
from barberia.booking.views import _generate_time_slots


def _future_date(days=1):
    return timezone.localdate() + timedelta(days=days)


class BookingViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Company.objects.create(
            nit="123",
            name="Test Barber",
            address="Calle 123",
            phone="555-0000",
            opening_time="09:00",
            closing_time="19:00",
        )
        cls.service = CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Corte de cabello",
            price=15000,
            duration_minutes=30,
            is_active=True,
        )
        CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Barba",
            price=8000,
            duration_minutes=20,
            is_active=True,
        )
        CatalogItem.objects.create(
            kind=CatalogItem.Kind.SERVICE,
            name="Inactivo",
            price=0,
            duration_minutes=30,
            is_active=False,
        )
        cls.barber = Employee.objects.create(
            full_name="Carlos Barbero",
            document_id="DOC-001",
            phone="555-1000",
        )
        User = get_user_model()
        cls.staff_user = User.objects.create_user(
            username="staff",
            password="testpass123",
            is_staff=True,
        )

    def test_service_list_shows_active_services(self):
        resp = self.client.get(reverse("booking:service_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Corte de cabello")
        self.assertContains(resp, "Barba")
        self.assertNotContains(resp, "Inactivo")
        self.assertIn("services", resp.context)
        self.assertEqual(len(resp.context["services"]), 2)

    def test_booking_form_get(self):
        resp = self.client.get(
            reverse("booking:booking_form", args=[self.service.id])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Corte de cabello")
        self.assertEqual(resp.context["step"], 2)
        self.assertIsInstance(resp.context["form"].fields["time"].choices, list)

    def test_booking_form_get_inactive_service_404(self):
        inactive = CatalogItem.objects.get(name="Inactivo")
        resp = self.client.get(
            reverse("booking:booking_form", args=[inactive.id])
        )
        self.assertEqual(resp.status_code, 404)

    def test_booking_form_post_valid_redirects(self):
        future = _future_date()
        resp = self.client.post(
            reverse("booking:booking_form", args=[self.service.id]),
            {
                "date": future.isoformat(),
                "time": "09:00",
                "full_name": "Miguel Pérez",
                "email": "miguel@example.com",
                "phone": "555-1234",
                "notes": "Sin barba",
            },
        )
        self.assertRedirects(
            resp, reverse("booking:booking_confirm", args=[self.service.id])
        )
        session = self.client.session
        self.assertIn("booking_data", session)
        self.assertEqual(session["booking_data"]["full_name"], "Miguel Pérez")

    def test_booking_form_post_invalid_date(self):
        yesterday = _future_date(days=-2)
        resp = self.client.post(
            reverse("booking:booking_form", args=[self.service.id]),
            {
                "date": yesterday.isoformat(),
                "time": "09:00",
                "full_name": "Test",
                "email": "test@example.com",
                "phone": "555-0000",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "La fecha no puede ser en el pasado.")

    def test_booking_form_post_missing_required_fields(self):
        future = _future_date()
        resp = self.client.post(
            reverse("booking:booking_form", args=[self.service.id]),
            {"date": future.isoformat(), "time": "10:00"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Este campo es obligatorio.")

    def test_booking_confirm_no_session_redirects(self):
        resp = self.client.get(
            reverse("booking:booking_confirm", args=[self.service.id])
        )
        self.assertRedirects(resp, reverse("booking:service_list"))

    def test_booking_confirm_get_shows_data(self):
        session = self.client.session
        future = _future_date()
        session["booking_data"] = {
            "service_id": self.service.id,
            "date": future.isoformat(),
            "time": "10:30",
            "full_name": "Ana López",
            "email": "ana@example.com",
            "phone": "555-5678",
            "notes": "",
        }
        session.save()

        resp = self.client.get(
            reverse("booking:booking_confirm", args=[self.service.id])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Ana López")
        self.assertContains(resp, "10:30")
        self.assertContains(resp, "Corte de cabello")
        self.assertEqual(resp.context["step"], 3)

    def test_booking_confirm_creates_sale(self):
        future = _future_date()
        session = self.client.session
        session["booking_data"] = {
            "service_id": self.service.id,
            "date": future.isoformat(),
            "time": "14:00",
            "full_name": "Pedro Ramírez",
            "email": "pedro@example.com",
            "phone": "555-9999",
            "notes": "Llegaré 10 min tarde",
        }
        session.save()

        resp = self.client.post(
            reverse("booking:booking_confirm", args=[self.service.id]),
            {"confirm": "1"},
        )
        sale = Sale.objects.filter(
            client__email__iexact="pedro@example.com"
        ).first()
        self.assertIsNotNone(sale)
        self.assertRedirects(
            resp, reverse("booking:booking_done", args=[sale.id])
        )
        self.assertEqual(sale.status, Sale.Status.SCHEDULED)
        self.assertEqual(sale.product, self.service)
        self.assertEqual(sale.product_price, self.service.price)
        self.assertEqual(sale.notes, "Llegaré 10 min tarde")
        self.assertEqual(sale.performed_by, self.staff_user)

    def test_booking_confirm_reuses_existing_client_by_email(self):
        client = Client.objects.create(
            full_name="Original Name",
            email="existing@example.com",
            phone="111-1111",
        )
        future = _future_date()
        session = self.client.session
        session["booking_data"] = {
            "service_id": self.service.id,
            "date": future.isoformat(),
            "time": "11:00",
            "full_name": "Updated Name",
            "email": "EXISTING@example.com",
            "phone": "222-2222",
            "notes": "",
        }
        session.save()
        self.client.post(
            reverse("booking:booking_confirm", args=[self.service.id]),
            {"confirm": "1"},
        )
        client.refresh_from_db()
        self.assertIn(client.full_name, ("Updated Name", "Original Name"))

    def test_booking_done_shows_sale(self):
        future = _future_date()
        client = Client.objects.create(
            full_name="Done Test",
            email="done@example.com",
            phone="555-0000",
        )
        scheduled_dt = timezone.make_aware(
            timezone.datetime.combine(future, timezone.datetime.min.time())
        )
        sale = Sale.objects.create(
            client=client,
            product=self.service,
            performed_by=self.staff_user,
            scheduled_for=scheduled_dt,
            status=Sale.Status.SCHEDULED,
            product_price=self.service.price,
        )
        resp = self.client.get(
            reverse("booking:booking_done", args=[sale.id])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Done Test")
        self.assertContains(resp, "Corte de cabello")

    def test_full_booking_flow(self):
        future = _future_date()

        resp = self.client.get(reverse("booking:service_list"))
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get(
            reverse("booking:booking_form", args=[self.service.id])
        )
        self.assertEqual(resp.status_code, 200)

        resp = self.client.post(
            reverse("booking:booking_form", args=[self.service.id]),
            {
                "date": future.isoformat(),
                "time": "16:00",
                "full_name": "Flow Test",
                "email": "flow@example.com",
                "phone": "555-FLOW",
                "notes": "",
            },
        )
        self.assertRedirects(
            resp, reverse("booking:booking_confirm", args=[self.service.id])
        )

        resp = self.client.get(
            reverse("booking:booking_confirm", args=[self.service.id])
        )
        self.assertEqual(resp.status_code, 200)

        resp = self.client.post(
            reverse("booking:booking_confirm", args=[self.service.id]),
            {"confirm": "1"},
        )
        sale = Sale.objects.get(client__email__iexact="flow@example.com")
        self.assertRedirects(
            resp, reverse("booking:booking_done", args=[sale.id])
        )

        resp = self.client.get(
            reverse("booking:booking_done", args=[sale.id])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Flow Test")

    def test_time_slots_respect_business_hours(self):
        services = _generate_time_slots(self.service, _future_date())
        self.assertNotEqual(len(services), 0)
        for label, value in services:
            hour = int(value.split(":")[0])
            self.assertGreaterEqual(hour, 9)
            self.assertLess(hour, 19)

    def test_time_slots_no_company(self):
        Company.objects.all().delete()
        slots = _generate_time_slots(self.service, _future_date())
        self.assertEqual(slots, [])

    def test_api_slots_returns_slots_for_valid_date(self):
        future = _future_date()
        resp = self.client.get(
            reverse("booking:api_slots", args=[self.service.id, future.isoformat()])
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("slots", data)
        self.assertGreater(len(data["slots"]), 0)
        self.assertEqual(data["slots"][0]["value"], "09:00")

    def test_api_slots_404_for_invalid_service(self):
        resp = self.client.get(
            reverse("booking:api_slots", args=[9999, "2026-06-01"])
        )
        self.assertEqual(resp.status_code, 404)

    def test_api_slots_404_for_inactive_service(self):
        inactive = CatalogItem.objects.get(name="Inactivo")
        future = _future_date()
        resp = self.client.get(
            reverse("booking:api_slots", args=[inactive.id, future.isoformat()])
        )
        self.assertEqual(resp.status_code, 404)

    def test_api_slots_400_for_bad_date(self):
        resp = self.client.get(
            reverse("booking:api_slots", args=[self.service.id, "not-a-date"])
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertIn("error", data)

    def test_api_client_lookup_returns_existing_client(self):
        Client.objects.create(
            full_name="Cliente Demo",
            email="demo@example.com",
            phone="555-7777",
        )
        resp = self.client.get(
            reverse("booking:api_client_lookup") + "?email=DEMO@example.com"
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["found"])
        self.assertEqual(data["client"]["full_name"], "Cliente Demo")
        self.assertEqual(data["client"]["phone"], "555-7777")

    def test_api_client_lookup_returns_not_found(self):
        resp = self.client.get(
            reverse("booking:api_client_lookup") + "?email=missing@example.com"
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["found"])

    def test_api_slots_empty_for_past_date(self):
        past = _future_date(days=-5)
        resp = self.client.get(
            reverse("booking:api_slots", args=[self.service.id, past.isoformat()])
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["slots"]), 0)

    def test_api_slots_with_barber_filter(self):
        future = _future_date()
        resp = self.client.get(
            reverse("booking:api_slots", args=[self.service.id, future.isoformat()])
            + f"?barber={self.barber.id}"
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreater(len(data["slots"]), 0)
        self.assertEqual(data["slots"][0]["value"], "09:00")

    def test_api_slots_respects_barber_occupancy(self):
        future = _future_date()
        at9 = timezone.make_aware(
            timezone.datetime.combine(future, timezone.datetime.min.time().replace(hour=9))
        )
        Sale.objects.create(
            client=None,
            product=self.service,
            employee=self.barber,
            performed_by=self.staff_user,
            scheduled_for=at9,
            status=Sale.Status.SCHEDULED,
            product_price=self.service.price,
        )
        at10 = timezone.make_aware(
            timezone.datetime.combine(future, timezone.datetime.min.time().replace(hour=10))
        )
        Sale.objects.create(
            client=None,
            product=self.service,
            performed_by=self.staff_user,
            scheduled_for=at10,
            status=Sale.Status.SCHEDULED,
            product_price=self.service.price,
        )
        resp = self.client.get(
            reverse("booking:api_slots", args=[self.service.id, future.isoformat()])
        )
        data_all = resp.json()
        resp_barber = self.client.get(
            reverse("booking:api_slots", args=[self.service.id, future.isoformat()])
            + f"?barber={self.barber.id}"
        )
        data_barber = resp_barber.json()
        self.assertGreater(len(data_all["slots"]), 0)
        self.assertGreater(len(data_barber["slots"]), 0)
        self.assertLess(len(data_all["slots"]), len(data_barber["slots"]))
        self.assertNotIn("09:00", [s["value"] for s in data_barber["slots"]])

    def test_booking_confirm_sets_employee(self):
        future = _future_date()
        session = self.client.session
        session["booking_data"] = {
            "service_id": self.service.id,
            "date": future.isoformat(),
            "time": "15:00",
            "full_name": "Barber Test",
            "email": "barber@example.com",
            "phone": "555-BARBER",
            "notes": "",
            "barber_id": self.barber.id,
            "barber_name": self.barber.full_name,
        }
        session.save()
        self.client.post(
            reverse("booking:booking_confirm", args=[self.service.id]),
            {"confirm": "1"},
        )
        sale = Sale.objects.get(client__email__iexact="barber@example.com")
        self.assertEqual(sale.employee, self.barber)

    # --- day_off and api_barbers tests ---

    def _next_weekday(self, target_weekday):
        """Return a future date falling on target_weekday (0=Mon..6=Sun)."""
        d = _future_date()
        while d.weekday() != target_weekday:
            d += timedelta(days=1)
        return d

    def test_api_barbers_returns_available_barbers(self):
        future = _future_date()
        resp = self.client.get(
            reverse("booking:api_barbers", args=[future.isoformat()])
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("barbers", data)
        barber_ids = [b["id"] for b in data["barbers"]]
        self.assertIn(self.barber.id, barber_ids)

    def test_api_barbers_excludes_barber_on_day_off(self):
        monday = self._next_weekday(0)
        self.barber.day_off = 0
        self.barber.save(update_fields=["day_off"])
        resp = self.client.get(
            reverse("booking:api_barbers", args=[monday.isoformat()])
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        barber_ids = [b["id"] for b in data["barbers"]]
        self.assertNotIn(self.barber.id, barber_ids)

    def test_api_barbers_400_bad_date(self):
        resp = self.client.get(
            reverse("booking:api_barbers", args=["not-a-date"])
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.json())

    def test_api_slots_empty_on_barber_day_off(self):
        monday = self._next_weekday(0)
        self.barber.day_off = 0
        self.barber.save(update_fields=["day_off"])
        resp = self.client.get(
            reverse("booking:api_slots", args=[self.service.id, monday.isoformat()])
            + f"?barber={self.barber.id}"
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["slots"]), 0)

    def test_generate_time_slots_empty_on_day_off(self):
        monday = self._next_weekday(0)
        self.barber.day_off = 0
        self.barber.save(update_fields=["day_off"])
        slots = _generate_time_slots(self.service, monday, barber=self.barber)
        self.assertEqual(slots, [])

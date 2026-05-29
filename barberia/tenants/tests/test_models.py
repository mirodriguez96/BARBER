from django.db import IntegrityError
from django.test import TestCase

from barberia.tenants.models import Domain, Tenant


class TenantModelTest(TestCase):
    def test_create_tenant(self):
        tenant = Tenant.objects.create(
            schema_name="luxor",
            db_name="barber_luxor",
            name="Luxor Barbería",
            nit="1234567890",
        )
        self.assertEqual(tenant.schema_name, "luxor")
        self.assertEqual(tenant.db_name, "barber_luxor")
        self.assertEqual(tenant.name, "Luxor Barbería")
        self.assertEqual(tenant.nit, "1234567890")

    def test_is_active_default_true(self):
        tenant = Tenant.objects.create(
            schema_name="luxor",
            db_name="barber_luxor",
            name="Luxor",
            nit="1111111111",
        )
        self.assertTrue(tenant.is_active)

    def test_nit_blank_default(self):
        tenant = Tenant.objects.create(
            schema_name="luxor",
            db_name="barber_luxor",
            name="Luxor",
            nit="",
        )
        self.assertEqual(tenant.nit, "")

    def test_created_at_auto_now_add(self):
        tenant = Tenant.objects.create(
            schema_name="luxor",
            db_name="barber_luxor",
            name="Luxor",
            nit="2222222222",
        )
        self.assertIsNotNone(tenant.created_at)

    def test_str_representation(self):
        tenant = Tenant.objects.create(
            schema_name="luxor",
            db_name="barber_luxor",
            name="Luxor Barbería",
            nit="3333333333",
        )
        self.assertEqual(str(tenant), "Luxor Barbería (luxor)")

    def test_schema_name_unique(self):
        Tenant.objects.create(
            schema_name="luxor",
            db_name="barber_luxor",
            name="Luxor",
            nit="4444444444",
        )
        with self.assertRaises(IntegrityError):
            Tenant.objects.create(
                schema_name="luxor",
                db_name="barber_luxor_2",
                name="Luxor Dup",
                nit="5555555555",
            )

    def test_db_name_unique(self):
        Tenant.objects.create(
            schema_name="luxor",
            db_name="barber_luxor",
            name="Luxor",
            nit="6666666666",
        )
        with self.assertRaises(IntegrityError):
            Tenant.objects.create(
                schema_name="luxor_2",
                db_name="barber_luxor",
                name="Luxor Dup",
                nit="7777777777",
            )

    def test_nit_unique(self):
        Tenant.objects.create(
            schema_name="luxor",
            db_name="barber_luxor",
            name="Luxor",
            nit="1234567890",
        )
        with self.assertRaises(IntegrityError):
            Tenant.objects.create(
                schema_name="stilo",
                db_name="barber_stilo",
                name="Stilo",
                nit="1234567890",
            )

    def test_multiple_tenants_have_different_created_at(self):
        t1 = Tenant.objects.create(
            schema_name="a", db_name="barber_a", name="A", nit="aaaaaaaaaa"
        )
        t2 = Tenant.objects.create(
            schema_name="b", db_name="barber_b", name="B", nit="bbbbbbbbbb"
        )
        self.assertLess(t1.created_at, t2.created_at)

    def test_verbose_name_plural(self):
        self.assertEqual(Tenant._meta.verbose_name_plural, "Empresas")


class DomainModelTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            schema_name="luxor",
            db_name="barber_luxor",
            name="Luxor",
            nit="1111111111",
        )

    def test_create_domain(self):
        domain = Domain.objects.create(
            domain="luxor.colstyle.com", tenant=self.tenant, is_primary=True
        )
        self.assertEqual(domain.domain, "luxor.colstyle.com")
        self.assertEqual(domain.tenant, self.tenant)
        self.assertTrue(domain.is_primary)

    def test_is_primary_default_true(self):
        domain = Domain.objects.create(domain="luxor.colstyle.com", tenant=self.tenant)
        self.assertTrue(domain.is_primary)

    def test_str_representation(self):
        domain = Domain.objects.create(domain="luxor.colstyle.com", tenant=self.tenant)
        self.assertEqual(str(domain), "luxor.colstyle.com")

    def test_domain_unique(self):
        Domain.objects.create(domain="luxor.colstyle.com", tenant=self.tenant)
        with self.assertRaises(IntegrityError):
            Domain.objects.create(domain="luxor.colstyle.com", tenant=self.tenant)

    def test_tenant_cascade_delete(self):
        Domain.objects.create(domain="luxor.colstyle.com", tenant=self.tenant)
        self.tenant.delete()
        self.assertEqual(Domain.objects.count(), 0)

    def test_related_name_domains(self):
        Domain.objects.create(domain="luxor.colstyle.com", tenant=self.tenant)
        Domain.objects.create(
            domain="www.luxor.colstyle.com", tenant=self.tenant, is_primary=False
        )
        self.assertEqual(self.tenant.domains.count(), 2)

    def test_domain_unique_across_tenants(self):
        other = Tenant.objects.create(
            schema_name="stilo",
            db_name="barber_stilo",
            name="Stilo",
            nit="2222222222",
        )
        Domain.objects.create(domain="luxor.colstyle.com", tenant=self.tenant)
        with self.assertRaises(IntegrityError):
            Domain.objects.create(domain="luxor.colstyle.com", tenant=other)

    def test_verbose_name_plural(self):
        self.assertEqual(Domain._meta.verbose_name_plural, "Dominios")

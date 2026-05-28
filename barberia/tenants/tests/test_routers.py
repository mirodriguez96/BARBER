from django.test import TestCase

from barberia.accounts.models import User
from barberia.common.models import Company
from barberia.routers import TenantRouter, get_current_db_name, set_current_db_name
from barberia.tenants.models import Tenant


class TenantRouterAppLabelTest(TestCase):
    def setUp(self):
        self.router = TenantRouter()

    def tearDown(self):
        set_current_db_name(None)

    def test_tenants_model_read_goes_to_default(self):
        set_current_db_name("barber_luxor")
        db = self.router.db_for_read(Tenant)
        self.assertEqual(db, "default")

    def test_non_tenant_model_read_uses_current_db(self):
        set_current_db_name("barber_luxor")
        db = self.router.db_for_read(User)
        self.assertEqual(db, "barber_luxor")

    def test_non_tenant_model_read_fallsback_to_default(self):
        set_current_db_name(None)
        db = self.router.db_for_read(User)
        self.assertEqual(db, "default")

    def test_tenants_model_write_goes_to_default(self):
        set_current_db_name("barber_luxor")
        db = self.router.db_for_write(Tenant)
        self.assertEqual(db, "default")

    def test_non_tenant_model_write_uses_current_db(self):
        set_current_db_name("barber_luxor")
        db = self.router.db_for_write(Company)
        self.assertEqual(db, "barber_luxor")

    def test_non_tenant_model_write_fallsback_to_default(self):
        set_current_db_name(None)
        db = self.router.db_for_write(Company)
        self.assertEqual(db, "default")

    def test_allow_relation_tenants_with_other(self):
        result = self.router.allow_relation(Tenant(), User())
        self.assertIs(result, True)

    def test_allow_relation_both_non_tenants(self):
        result = self.router.allow_relation(User(), Company())
        self.assertIsNone(result)

    def test_allow_migrate_default_db_any_app(self):
        self.assertIs(self.router.allow_migrate("default", "accounts"), True)
        self.assertIs(self.router.allow_migrate("default", "tenants"), True)

    def test_allow_migrate_tenant_db_other_apps(self):
        self.assertIs(self.router.allow_migrate("barber_luxor", "accounts"), True)

    def test_allow_migrate_tenants_app_to_tenant_db_blocked(self):
        self.assertIs(self.router.allow_migrate("barber_luxor", "tenants"), False)

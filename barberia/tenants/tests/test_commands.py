from unittest.mock import MagicMock, patch

from django.core.management.base import CommandError
from django.test import TestCase

from barberia.tenants.management.commands.register_tenant import (
    Command as RegisterTenantCommand,
)
from barberia.tenants.models import Domain, Tenant


class RegisterTenantCommandTest(TestCase):
    def setUp(self):
        self.default_kwargs = {
            "schema_name": "luxor",
            "name": "Luxor Barbería",
            "nit": "1234567890",
            "admin_password": "admin123",
            "admin_username": "admin",
            "admin_email": "admin@luxor.colstyle.com",
            "domain": "luxor.colstyle.com",
            "db_name": "barber_luxor",
        }

    def _run_command(self, **overrides):
        kwargs = {**self.default_kwargs, **overrides}
        cmd = RegisterTenantCommand()
        cmd.stdout = MagicMock()
        with (
            patch.object(RegisterTenantCommand, "_create_database") as mock_create,
            patch.object(RegisterTenantCommand, "_configure_database") as mock_config,
            patch(
                "barberia.tenants.management.commands.register_tenant.call_command"
            ) as mock_migrate,
            patch(
                "barberia.tenants.management.commands.register_tenant.get_user_model"
            ) as mock_get_user,
        ):
            mock_user = MagicMock()
            mock_user.Role.ADMIN = "admin"
            mock_get_user.return_value = mock_user
            cmd.handle(**kwargs)
        return mock_create, mock_config, mock_migrate, mock_user

    def test_success_path(self):
        mock_create, mock_config, mock_migrate, mock_user = self._run_command()

        mock_create.assert_called_once_with("barber_luxor")
        mock_config.assert_called_once_with("barber_luxor")
        mock_migrate.assert_called_once_with(
            "migrate", database="barber_luxor", verbosity=1
        )

        tenant = Tenant.objects.get(schema_name="luxor")
        self.assertEqual(tenant.name, "Luxor Barbería")
        self.assertEqual(tenant.nit, "1234567890")
        self.assertEqual(tenant.db_name, "barber_luxor")
        self.assertTrue(tenant.is_active)

        domain = Domain.objects.get(domain="luxor.colstyle.com")
        self.assertEqual(domain.tenant, tenant)
        self.assertTrue(domain.is_primary)

    def test_superuser_created(self):
        _, _, _, mock_user = self._run_command()
        mock_user.objects.db_manager.return_value.create_superuser.assert_called_once_with(
            username="admin",
            password="admin123",
            email="admin@luxor.colstyle.com",
            role="admin",
        )

    def test_custom_db_name(self):
        mock_create, mock_config, _, _ = self._run_command(db_name="custom_db")
        mock_create.assert_called_once_with("custom_db")
        mock_config.assert_called_once_with("custom_db")
        tenant = Tenant.objects.get(schema_name="luxor")
        self.assertEqual(tenant.db_name, "custom_db")

    def test_custom_domain(self):
        self._run_command(domain="luxor.micolstyle.com")
        domain = Domain.objects.get(domain="luxor.micolstyle.com")
        self.assertEqual(domain.tenant.schema_name, "luxor")

    def test_custom_admin_username(self):
        self._run_command(admin_username="superadmin")
        tenant = Tenant.objects.get(schema_name="luxor")
        self.assertEqual(tenant.schema_name, "luxor")

    def test_duplicate_schema_name_raises_error(self):
        self._run_command()
        with self.assertRaises(CommandError):
            self._run_command()

    def test_duplicate_db_name_raises_error(self):
        self._run_command()
        with self.assertRaises(CommandError):
            self._run_command(
                schema_name="other",
                nit="9999999999",
                domain="other.colstyle.com",
            )

    def test_success_message_in_output(self):
        cmd = RegisterTenantCommand()
        from io import StringIO

        cmd.stdout = StringIO()
        with (
            patch.object(RegisterTenantCommand, "_create_database"),
            patch.object(RegisterTenantCommand, "_configure_database"),
            patch("barberia.tenants.management.commands.register_tenant.call_command"),
            patch(
                "barberia.tenants.management.commands.register_tenant.get_user_model"
            ),
        ):
            cmd.handle(**self.default_kwargs)
        output = cmd.stdout.getvalue()
        self.assertIn("registrado exitosamente", output)
        self.assertIn("Luxor Barbería", output)

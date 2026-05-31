from io import StringIO
from unittest import mock

from django.test import TestCase

from barberia.accounts.models import User
from barberia.dashboard.management.commands.seed_permissions import Command
from barberia.dashboard.models import RoleCrudPermission, RoleMenuPermission


class SeedPermissionsCommandTest(TestCase):
    def setUp(self):
        self.cmd = Command()
        self.cmd.stdout = StringIO()
        self.cmd._ensure_database = lambda db_name: None
        self._patcher = mock.patch(
            "barberia.dashboard.management.commands.seed_permissions.set_current_db_name"
        )
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()

    def test_creates_menu_permissions_for_barbero_and_estilista(self):
        self.cmd.handle(tenant="test")
        barbero_menu_count = RoleMenuPermission.objects.filter(
            role=User.Role.BARBERO
        ).count()
        estilista_menu_count = RoleMenuPermission.objects.filter(
            role=User.Role.ESTILISTA
        ).count()
        self.assertEqual(barbero_menu_count, 4)
        self.assertEqual(estilista_menu_count, 4)

    def test_restricted_keys_not_created(self):
        self.cmd.handle(tenant="test")
        restricted = {"sales", "compras", "inventory"}
        for perm in RoleMenuPermission.objects.all():
            self.assertNotIn(perm.menu_key, restricted)

    def test_allowed_keys_created(self):
        self.cmd.handle(tenant="test")
        allowed = {"barbers", "catalog", "payments", "config"}
        created_barbero = set(
            RoleMenuPermission.objects.filter(role=User.Role.BARBERO).values_list(
                "menu_key", flat=True
            )
        )
        created_estilista = set(
            RoleMenuPermission.objects.filter(role=User.Role.ESTILISTA).values_list(
                "menu_key", flat=True
            )
        )
        self.assertEqual(created_barbero, allowed)
        self.assertEqual(created_estilista, allowed)

    def test_creates_crud_permissions_for_all_apps_and_actions(self):
        self.cmd.handle(tenant="test")
        apps = ["personal", "productos", "ventas", "compras"]
        actions = ["registrar", "modificar", "desactivar"]
        expected_count = len(apps) * len(actions)
        barbero_crud = RoleCrudPermission.objects.filter(role=User.Role.BARBERO)
        estilista_crud = RoleCrudPermission.objects.filter(role=User.Role.ESTILISTA)
        self.assertEqual(barbero_crud.count(), expected_count)
        self.assertEqual(estilista_crud.count(), expected_count)

    def test_no_admin_permissions_created(self):
        self.cmd.handle(tenant="test")
        admin_menu = RoleMenuPermission.objects.filter(role=User.Role.ADMIN)
        admin_crud = RoleCrudPermission.objects.filter(role=User.Role.ADMIN)
        self.assertEqual(admin_menu.count(), 0)
        self.assertEqual(admin_crud.count(), 0)

    def test_idempotent_running_twice(self):
        self.cmd.handle(tenant="test")
        first_count = RoleMenuPermission.objects.count()
        self.cmd.stdout = StringIO()
        self.cmd.handle(tenant="test")
        second_count = RoleMenuPermission.objects.count()
        self.assertEqual(first_count, second_count)

    def test_success_message_with_counts(self):
        self.cmd.handle(tenant="test")
        output = self.cmd.stdout.getvalue()
        self.assertIn("test", output)
        self.assertIn("8 menú", output)
        self.assertIn("24 acciones", output)

from django.db import IntegrityError
from django.test import TestCase

from barberia.accounts.models import User
from barberia.dashboard.models import RoleCrudPermission, RoleMenuPermission


class RoleMenuPermissionModelTest(TestCase):
    def setUp(self):
        self.perm = RoleMenuPermission.objects.create(
            role=User.Role.BARBERO,
            menu_key="overview",
        )

    def test_create_permission(self):
        self.assertEqual(self.perm.role, User.Role.BARBERO)
        self.assertEqual(self.perm.menu_key, "overview")

    def test_str_representation(self):
        self.assertEqual(str(self.perm), "barbero -> overview")

    def test_unique_together_violation(self):
        with self.assertRaises(IntegrityError):
            RoleMenuPermission.objects.create(
                role=User.Role.BARBERO,
                menu_key="overview",
            )

    def test_estilista_role_allowed(self):
        perm = RoleMenuPermission.objects.create(
            role=User.Role.ESTILISTA,
            menu_key="barbers",
        )
        self.assertEqual(perm.role, User.Role.ESTILISTA)

    def test_multiple_keys_same_role(self):
        keys = ["barbers", "catalog", "payments", "config"]
        for key in keys:
            RoleMenuPermission.objects.create(role=User.Role.BARBERO, menu_key=key)
        count = RoleMenuPermission.objects.filter(role=User.Role.BARBERO).count()
        self.assertEqual(count, len(keys) + 1)

    def test_admin_role_also_storable(self):
        perm = RoleMenuPermission.objects.create(
            role=User.Role.ADMIN,
            menu_key="sales",
        )
        self.assertEqual(perm.role, User.Role.ADMIN)

    def test_filter_by_role(self):
        RoleMenuPermission.objects.create(
            role=User.Role.ESTILISTA,
            menu_key="catalog",
        )
        barbero_perms = RoleMenuPermission.objects.filter(role=User.Role.BARBERO)
        estilista_perms = RoleMenuPermission.objects.filter(role=User.Role.ESTILISTA)
        self.assertEqual(barbero_perms.count(), 1)
        self.assertEqual(estilista_perms.count(), 1)

    def test_values_list_flat(self):
        keys = set(
            RoleMenuPermission.objects.filter(role=User.Role.BARBERO).values_list(
                "menu_key", flat=True
            )
        )
        self.assertIn("overview", keys)


class RoleCrudPermissionModelTest(TestCase):
    def setUp(self):
        self.perm = RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key=RoleCrudPermission.AppKey.PERSONAL,
            action=RoleCrudPermission.Action.REGISTRAR,
        )

    def test_create_permission(self):
        self.assertEqual(self.perm.role, User.Role.BARBERO)
        self.assertEqual(self.perm.app_key, "personal")
        self.assertEqual(self.perm.action, "registrar")

    def test_str_representation(self):
        self.assertEqual(str(self.perm), "barbero -> personal:registrar")

    def test_unique_together_violation(self):
        with self.assertRaises(IntegrityError):
            RoleCrudPermission.objects.create(
                role=User.Role.BARBERO,
                app_key=RoleCrudPermission.AppKey.PERSONAL,
                action=RoleCrudPermission.Action.REGISTRAR,
            )

    def test_all_app_keys(self):
        expected = {"personal", "productos", "ventas", "compras"}
        actual = {k.value for k in RoleCrudPermission.AppKey}
        self.assertEqual(actual, expected)

    def test_all_actions(self):
        expected = {"registrar", "modificar", "desactivar"}
        actual = {a.value for a in RoleCrudPermission.Action}
        self.assertEqual(actual, expected)

    def test_estilista_role_allowed(self):
        perm = RoleCrudPermission.objects.create(
            role=User.Role.ESTILISTA,
            app_key=RoleCrudPermission.AppKey.PRODUCTOS,
            action=RoleCrudPermission.Action.MODIFICAR,
        )
        self.assertEqual(perm.role, User.Role.ESTILISTA)

    def test_same_role_different_app_and_action(self):
        RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key=RoleCrudPermission.AppKey.VENTAS,
            action=RoleCrudPermission.Action.DESACTIVAR,
        )
        count = RoleCrudPermission.objects.filter(role=User.Role.BARBERO).count()
        self.assertEqual(count, 2)

    def test_filter_by_app_key(self):
        RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key=RoleCrudPermission.AppKey.COMPRAS,
            action=RoleCrudPermission.Action.MODIFICAR,
        )
        personal = RoleCrudPermission.objects.filter(
            app_key=RoleCrudPermission.AppKey.PERSONAL
        )
        self.assertEqual(personal.count(), 1)

    def test_choices_match_user_role_choices(self):
        role_values = {c[0] for c in User.Role.choices}
        perm_role_values = {
            c[0] for c in RoleCrudPermission._meta.get_field("role").choices
        }
        self.assertEqual(role_values, perm_role_values)

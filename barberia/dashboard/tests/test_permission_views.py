from django.test import TestCase
from django.urls import reverse

from barberia.accounts.models import User
from barberia.dashboard.models import RoleCrudPermission, RoleMenuPermission


class PermissionConfigViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="admin",
            password="pass1234",
            role=User.Role.ADMIN,
        )
        self.barbero = User.objects.create_user(
            username="barbero",
            password="pass1234",
            role=User.Role.BARBERO,
        )
        self.client.login(username="admin", password="pass1234")
        self.list_url = reverse("dashboard:home")

    def _config_url(self, config_tab="permissions", **params):
        params.update({"section": "config", "config_tab": config_tab})
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.list_url}?{qs}"

    # --- Menu permissions tab GET ---

    def test_permissions_tab_renders_for_admin(self):
        response = self.client.get(self._config_url("permissions"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("permission_matrix", response.context)
        self.assertIn("permission_menu_items", response.context)

    def test_permissions_tab_contains_matrix(self):
        RoleMenuPermission.objects.create(role=User.Role.BARBERO, menu_key="overview")
        response = self.client.get(self._config_url("permissions"))
        matrix = response.context["permission_matrix"]
        self.assertIn(User.Role.BARBERO, matrix)
        self.assertIn(User.Role.ESTILISTA, matrix)

    def test_permissions_tab_redirects_non_admin(self):
        self.client.login(username="barbero", password="pass1234")
        RoleMenuPermission.objects.create(role=User.Role.BARBERO, menu_key="overview")
        response = self.client.get(self._config_url("permissions"))
        self.assertRedirects(response, f"{self.list_url}?section=overview")

    def test_permissions_tab_shows_config_tab_in_context(self):
        response = self.client.get(self._config_url("permissions"))
        self.assertEqual(response.context["config_tab"], "permissions")

    def test_permissions_tab_all_menu_keys_in_context(self):
        response = self.client.get(self._config_url("permissions"))
        all_keys = response.context["all_menu_keys"]
        expected = [
            "overview",
            "barbers",
            "catalog",
            "sales",
            "compras",
            "payments",
            "inventory",
            "config",
        ]
        self.assertEqual(all_keys, expected)

    def test_permissions_tab_permission_menu_items_in_context(self):
        response = self.client.get(self._config_url("permissions"))
        items = response.context["permission_menu_items"]
        keys = [i["key"] for i in items]
        self.assertNotIn("overview", keys)
        self.assertIn("sales", keys)

    # --- Menu permissions tab POST ---

    def test_permissions_post_creates_menu_permissions(self):
        response = self.client.post(
            self._config_url("permissions"),
            {
                f"perms_{User.Role.BARBERO}": ["overview", "barbers", "catalog"],
            },
        )
        self.assertRedirects(
            response,
            f"{self.list_url}?section=config&config_tab=permissions",
        )
        perms = RoleMenuPermission.objects.filter(role=User.Role.BARBERO)
        self.assertEqual(perms.count(), 3)
        keys = set(perms.values_list("menu_key", flat=True))
        self.assertEqual(keys, {"overview", "barbers", "catalog"})

    def test_permissions_post_removes_old_then_creates_new(self):
        RoleMenuPermission.objects.create(role=User.Role.BARBERO, menu_key="inventory")
        response = self.client.post(
            self._config_url("permissions"),
            {
                f"perms_{User.Role.BARBERO}": ["overview"],
                f"perms_{User.Role.ESTILISTA}": ["barbers"],
            },
        )
        self.assertRedirects(response, self._config_url("permissions"))
        self.assertEqual(
            RoleMenuPermission.objects.filter(role=User.Role.BARBERO).count(), 1
        )
        self.assertEqual(
            RoleMenuPermission.objects.filter(role=User.Role.ESTILISTA).count(), 1
        )

    def test_permissions_post_empty_clears_all(self):
        RoleMenuPermission.objects.create(role=User.Role.BARBERO, menu_key="overview")
        self.client.post(
            self._config_url("permissions"),
            {},
        )
        self.assertEqual(RoleMenuPermission.objects.count(), 0)

    def test_permissions_post_admin_role_never_included(self):
        self.client.post(
            self._config_url("permissions"),
            {f"perms_{User.Role.ADMIN}": ["overview"]},
        )
        admin_perms = RoleMenuPermission.objects.filter(role=User.Role.ADMIN)
        self.assertEqual(admin_perms.count(), 0)

    def test_permissions_post_success_message(self):
        response = self.client.post(
            self._config_url("permissions"),
            {f"perms_{User.Role.BARBERO}": ["overview"]},
            follow=True,
        )
        messages = list(response.context["messages"])
        self.assertTrue(any("actualizados" in str(m) for m in messages))

    # --- CRUD permissions tab GET ---

    def test_crud_permissions_tab_renders_for_admin(self):
        response = self.client.get(
            self._config_url("crud_permissions", crud_section="personal")
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("crud_section_matrix", response.context)
        self.assertIn("crud_apps", response.context)
        self.assertIn("crud_actions", response.context)
        self.assertEqual(response.context["current_crud_section"], "personal")

    def test_crud_permissions_tab_shows_matrix(self):
        RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key="personal",
            action="registrar",
        )
        response = self.client.get(
            self._config_url("crud_permissions", crud_section="personal")
        )
        matrix = response.context["crud_section_matrix"]
        barbero_row = next(r for r in matrix if r["role_key"] == User.Role.BARBERO)
        registrar_action = next(
            a for a in barbero_row["actions"] if a["key"] == "registrar"
        )
        self.assertTrue(registrar_action["checked"])

    def test_crud_permissions_tab_redirects_non_admin(self):
        self.client.login(username="barbero", password="pass1234")
        RoleMenuPermission.objects.create(role=User.Role.BARBERO, menu_key="overview")
        response = self.client.get(
            self._config_url("crud_permissions", crud_section="personal")
        )
        self.assertRedirects(response, f"{self.list_url}?section=overview")

    def test_crud_defaults_to_personal(self):
        response = self.client.get(
            f"{self.list_url}?section=config&config_tab=crud_permissions"
        )
        self.assertEqual(response.context["current_crud_section"], "personal")

    def test_crud_different_sections(self):
        for section in ["personal", "productos", "ventas", "compras"]:
            response = self.client.get(
                self._config_url("crud_permissions", crud_section=section)
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["current_crud_section"], section)

    # --- CRUD permissions tab POST ---

    def test_crud_permissions_post_creates_for_section(self):
        response = self.client.post(
            self._config_url("crud_permissions", crud_section="personal"),
            {
                "crud_section": "personal",
                f"crud_{User.Role.BARBERO}_personal_registrar": "on",
                f"crud_{User.Role.BARBERO}_personal_modificar": "on",
            },
        )
        self.assertRedirects(
            response,
            f"{self.list_url}?section=config&config_tab=crud_permissions&crud_section=personal",
        )
        perms = RoleCrudPermission.objects.filter(app_key="personal")
        self.assertEqual(perms.count(), 2)

    def test_crud_permissions_post_only_affects_section(self):
        RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key="productos",
            action="registrar",
        )
        self.client.post(
            self._config_url("crud_permissions", crud_section="personal"),
            {
                "crud_section": "personal",
                f"crud_{User.Role.BARBERO}_personal_registrar": "on",
            },
        )
        self.assertEqual(
            RoleCrudPermission.objects.filter(app_key="productos").count(), 1
        )
        self.assertEqual(
            RoleCrudPermission.objects.filter(app_key="personal").count(), 1
        )

    def test_crud_permissions_post_clears_section_before_create(self):
        RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key="personal",
            action="registrar",
        )
        RoleCrudPermission.objects.create(
            role=User.Role.BARBERO,
            app_key="personal",
            action="modificar",
        )
        self.client.post(
            self._config_url("crud_permissions", crud_section="personal"),
            {
                "crud_section": "personal",
            },
        )
        self.assertEqual(
            RoleCrudPermission.objects.filter(app_key="personal").count(), 0
        )

    def test_crud_permissions_post_admin_role_never_included(self):
        self.client.post(
            self._config_url("crud_permissions", crud_section="personal"),
            {
                "crud_section": "personal",
                f"crud_{User.Role.ADMIN}_personal_registrar": "on",
            },
        )
        admin_perms = RoleCrudPermission.objects.filter(role=User.Role.ADMIN)
        self.assertEqual(admin_perms.count(), 0)

    def test_crud_permissions_post_success_message(self):
        response = self.client.post(
            self._config_url("crud_permissions", crud_section="personal"),
            {
                "crud_section": "personal",
                f"crud_{User.Role.BARBERO}_personal_registrar": "on",
            },
            follow=True,
        )
        messages = list(response.context["messages"])
        self.assertTrue(any("acciones" in str(m) for m in messages))

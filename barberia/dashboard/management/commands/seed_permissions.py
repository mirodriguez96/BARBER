from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import OperationalError, connections

from barberia.accounts.models import User
from barberia.dashboard.models import RoleCrudPermission, RoleMenuPermission
from barberia.routers import set_current_db_name

ALL_MENU_KEYS = [
    "barbers",
    "catalog",
    "sales",
    "compras",
    "payments",
    "inventory",
    "config",
]

RESTRICTED_KEYS = {"sales", "compras", "inventory"}


class Command(BaseCommand):
    help = "Crea permisos de menú por defecto para roles no-admin"

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant",
            help="Nombre del tenant (ej: luxor → BD barber_luxor). "
            "Si no se especifica, aplica a todos los tenants activos.",
        )

    def _ensure_database(self, db_name):
        if db_name not in connections.databases:
            cfg = settings.DATABASES["default"]
            connections.databases[db_name] = {**cfg, "NAME": db_name}

    def _seed_tenant(self, tenant):
        db_name = f"barber_{tenant}"

        self._ensure_database(db_name)
        set_current_db_name(db_name)

        try:
            RoleMenuPermission.objects.all().delete()
            RoleCrudPermission.objects.all().delete()
        except OperationalError as e:
            self.stderr.write(
                self.style.WARNING(
                    f"Saltando tenant '{tenant}' (BD no disponible): {e}"
                )
            )
            return

        for role in [User.Role.BARBERO, User.Role.ESTILISTA]:
            for key in ALL_MENU_KEYS:
                if key not in RESTRICTED_KEYS:
                    RoleMenuPermission.objects.create(role=role, menu_key=key)

        CRUD_APPS = ["personal", "productos", "ventas", "compras"]
        CRUD_ACTIONS = ["registrar", "modificar", "desactivar"]

        for role in [User.Role.BARBERO, User.Role.ESTILISTA]:
            for app_key in CRUD_APPS:
                for action in CRUD_ACTIONS:
                    RoleCrudPermission.objects.create(
                        role=role, app_key=app_key, action=action
                    )

        created_menu = RoleMenuPermission.objects.count()
        created_crud = RoleCrudPermission.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Permisos creados para tenant '{tenant}': "
                f"{created_menu} menú, {created_crud} acciones"
            )
        )

    def handle(self, *args, **options):
        if options["tenant"]:
            self._seed_tenant(options["tenant"])
            return

        from barberia.tenants.models import Tenant

        tenants = Tenant.objects.using("default").filter(is_active=True)
        if not tenants.exists():
            self.stdout.write(self.style.WARNING("No hay tenants activos para seed."))
            return

        for tenant in tenants:
            self._seed_tenant(tenant.schema_name)

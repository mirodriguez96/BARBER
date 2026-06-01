from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import ProgrammingError, connections

from barberia.tenants.models import Tenant

BACKFILL_SALE = "UPDATE operations_sale SET codigo = CONCAT('VEN-', id) WHERE codigo = '' OR codigo IS NULL;"
BACKFILL_PURCHASE = "UPDATE operations_purchase SET codigo = CONCAT('COM-', id) WHERE codigo = '' OR codigo IS NULL;"


def _backfill_codigo(db_name):
    with connections[db_name].cursor() as c:
        c.execute(BACKFILL_SALE)
        c.execute(BACKFILL_PURCHASE)


class Command(BaseCommand):
    help = "Ejecuta migrate en todas las bases de datos de tenants activos"

    def handle(self, *args, **options):
        tenants = Tenant.objects.filter(is_active=True)
        if not tenants:
            self.stdout.write("No hay tenants activos para migrar")
            return

        for tenant in tenants:
            db_name = tenant.db_name
            if db_name not in connections.databases:
                cfg = connections.databases["default"]
                connections.databases[db_name] = {**cfg, "NAME": db_name}

            self.stdout.write(f"Migrando {tenant.name} ({db_name})...")

            # Backfill antes de migrate (por si la columna ya existe y hay filas vacías)
            try:
                _backfill_codigo(db_name)
            except ProgrammingError:
                pass  # columna codigo no existe aún, migrate la creará

            call_command("migrate", database=db_name, verbosity=1)

            # Backfill después de migrate (por si había columnas nuevas)
            _backfill_codigo(db_name)

        self.stdout.write(
            self.style.SUCCESS(f"Migración completada para {tenants.count()} tenants")
        )

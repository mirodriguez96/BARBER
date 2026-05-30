from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connections

from barberia.tenants.models import Tenant


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
            call_command("migrate", database=db_name, verbosity=1)

        self.stdout.write(
            self.style.SUCCESS(f"Migración completada para {tenants.count()} tenants")
        )

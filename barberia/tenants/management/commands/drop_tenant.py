from django.core.management.base import BaseCommand, CommandError
from django.db import connections

from barberia.tenants.models import Domain, Tenant

REGISTRY_DB = "barber_tenants_registry"


class Command(BaseCommand):
    help = "Elimina un tenant: corta conexiones, elimina BD, Domain y registro Tenant"

    def add_arguments(self, parser):
        parser.add_argument("schema_name", help="Identificador del subdominio. Ej: luxor")
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Confirmación explícita para eliminar el tenant",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Continuar aunque la BD no exista (no lanza error)",
        )

    def handle(self, *args, **options):
        schema_name = options["schema_name"]
        confirm = options["confirm"]
        force = options["force"]

        if not confirm:
            raise CommandError(
                "Debes pasar --confirm para confirmar la eliminación del tenant"
            )

        tenant = Tenant.objects.filter(schema_name=schema_name).first()
        if not tenant:
            raise CommandError(
                f"No existe un tenant con schema_name '{schema_name}'"
            )

        db_name = tenant.db_name

        if db_name == REGISTRY_DB:
            raise CommandError(
                f"No se puede eliminar la BD de registro '{REGISTRY_DB}'"
            )

        self.stdout.write(f"[1/4] Terminando conexiones activas a '{db_name}'...")
        self._terminate_connections(db_name, force)

        self.stdout.write(f"[2/4] Eliminando base de datos '{db_name}'...")
        self._drop_database(db_name, force)

        self.stdout.write("[3/4] Eliminando registros Domain...")
        Domain.objects.filter(tenant=tenant).delete()

        self.stdout.write("[4/4] Eliminando registro Tenant...")
        schema_pk = tenant.pk
        tenant.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Tenant '{schema_name}' (pk={schema_pk}) eliminado exitosamente"
            )
        )
        self.stdout.write()
        self.stdout.write("Próximos pasos:")
        self.stdout.write(f"  python manage.py register_tenant {schema_name} --name=... --admin-password=...")
        self.stdout.write(f"  python manage.py seed_data --tenant={schema_name}")

    def _terminate_connections(self, db_name, force):
        conn = connections["default"]
        with conn.cursor() as cursor:
            cursor.connection.autocommit = True
            cursor.execute(
                """
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = %s
                  AND pid <> pg_backend_pid()
                """,
                [db_name],
            )
            terminated = cursor.rowcount
            self.stdout.write(f"  Conexiones terminadas: {terminated}")

    def _drop_database(self, db_name, force):
        conn = connections["default"]
        with conn.cursor() as cursor:
            cursor.connection.autocommit = True
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", [db_name])
            exists = cursor.fetchone() is not None

            if not exists:
                if force:
                    self.stdout.write(f"  La BD '{db_name}' no existe, continuando (--force)...")
                    return
                raise CommandError(
                    f"La BD '{db_name}' no existe. Usa --force para ignorar este error"
                )

            cursor.execute(f'DROP DATABASE "{db_name}"')
            self.stdout.write(f"  BD '{db_name}' eliminada")

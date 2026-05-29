from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connections

from barberia.tenants.models import Domain, Tenant


class Command(BaseCommand):
    help = "Registra un nuevo tenant: crea BD, corre migrations, crea Domain y superusuario"

    def add_arguments(self, parser):
        parser.add_argument("schema_name", help="Identificador del subdominio. Ej: luxor")
        parser.add_argument("--name", required=True, help="Nombre comercial de la empresa")
        parser.add_argument("--nit", default="", help="NIT de la empresa")
        parser.add_argument("--domain", help="Dominio completo. Default: {schema_name}.colstyle.com")
        parser.add_argument("--db-name", help="Nombre de la BD. Default: barber_{schema_name}")
        parser.add_argument("--admin-username", default="admin", help="Username del superadmin del tenant (default: admin)")
        parser.add_argument("--admin-password", required=True, help="Password del superadmin del tenant")
        parser.add_argument("--admin-email", default="", help="Email del superadmin (default: admin@{schema_name}.colstyle.com)")

    def handle(self, *args, **options):
        schema_name = options["schema_name"]
        db_name = options.get("db_name") or f"barber_{schema_name}"
        domain = options.get("domain") or f"{schema_name}.colstyle.com"
        name = options["name"]
        nit = options.get("nit", "")
        admin_username = options["admin_username"]
        admin_password = options["admin_password"]
        admin_email = options.get("admin_email") or f"admin@{schema_name}.colstyle.com"

        if Tenant.objects.filter(schema_name=schema_name).exists():
            raise CommandError(f"Ya existe un tenant con schema_name '{schema_name}'")
        if Tenant.objects.filter(db_name=db_name).exists():
            raise CommandError(f"Ya existe un tenant con db_name '{db_name}'")

        self.stdout.write(f"[1/5] Creando base de datos '{db_name}'...")
        self._create_database(db_name)

        self.stdout.write("[2/5] Conectando y corriendo migraciones...")
        self._configure_database(db_name)
        call_command("migrate", database=db_name, verbosity=1)

        self.stdout.write("[3/5] Creando registro Tenant...")
        tenant = Tenant.objects.create(
            schema_name=schema_name,
            db_name=db_name,
            name=name,
            nit=nit,
            is_active=True,
        )

        self.stdout.write("[4/5] Creando Domain...")
        Domain.objects.create(domain=domain, tenant=tenant, is_primary=True)

        self.stdout.write("[5/5] Creando superusuario...")
        User = get_user_model()
        User.objects.db_manager(db_name).create_superuser(
            username=admin_username,
            password=admin_password,
            email=admin_email,
            role=User.Role.ADMIN,
        )

        self.stdout.write(self.style.SUCCESS(f"Tenant '{name}' registrado exitosamente"))
        self.stdout.write(f"  URL:      {domain}")
        self.stdout.write(f"  BD:       {db_name}")
        self.stdout.write(f"  Admin:    {admin_username} / {admin_password}")

    def _create_database(self, db_name):
        conn = connections["default"]
        cursor = conn.cursor()
        cursor.connection.autocommit = True
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", [db_name])
        if not cursor.fetchone():
            cursor.execute(f'CREATE DATABASE "{db_name}"')
        cursor.close()

    def _configure_database(self, db_name):
        cfg = settings.DATABASES["default"]
        connections.databases[db_name] = {**cfg, "NAME": db_name}

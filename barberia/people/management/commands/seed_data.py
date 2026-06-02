import random
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connections
from django.utils import timezone

from barberia.accounts.models import User
from barberia.catalog.models import CatalogItem
from barberia.common.models import Company
from barberia.inventory.models import InventoryMovement
from barberia.operations.models import Purchase, Sale
from barberia.people.models import Client, Employee
from barberia.routers import set_current_db_name


class Command(BaseCommand):
    help = "Pobla la BD de un tenant con datos de ejemplo"

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant",
            default="luxor",
            help="Nombre del tenant (ej: luxor → BD barber_luxor)",
        )
        parser.add_argument(
            "--days", type=int, default=7, help="Cuantos días hacia atrás poblar ventas"
        )
        parser.add_argument(
            "--reset-admin",
            action="store_true",
            default=True,
            help="Resetear contraseña admin",
        )

    def _ensure_database(self, db_name):
        if db_name not in connections.databases:
            cfg = settings.DATABASES["default"]
            connections.databases[db_name] = {**cfg, "NAME": db_name}

    def handle(self, *args, **options):
        tenant = options["tenant"]
        db_name = f"barber_{tenant}"
        days_back = options["days"]

        self._ensure_database(db_name)
        set_current_db_name(db_name)

        self.stdout.write(f"Conectado a BD: {db_name}")

        now = timezone.now()

        # --- Clean existing data (reverse dependency order) ---
        self.stdout.write("Limpiando datos existentes...")
        InventoryMovement.objects.all().delete()
        Sale.objects.all().delete()
        Purchase.objects.all().delete()
        CatalogItem.objects.all().delete()
        Client.objects.all().delete()
        Employee.objects.all().delete()
        User.objects.all().delete()
        Company.objects.all().delete()

        # --- Company ---
        Company.objects.create(
            nit="1234567890123",
            name=f"Barbería {tenant.title()}",
            address="Calle Principal #123",
            phone="+591 70000000",
            opening_time="09:00",
            closing_time="19:00",
        )
        self.stdout.write("  ✓ Company creada")

        # --- Users ---
        admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@barberia.com",
            password="admin123",
            role=User.Role.ADMIN,
            phone="+591 70000001",
            first_name="Admin",
            last_name="Principal",
        )

        barber_users = []
        barber_data = [
            ("carlos", "Carlos", "Mendoza"),
            ("juan", "Juan", "Perez"),
            ("miguel", "Miguel", "Torres"),
        ]
        for username, first, last in barber_data:
            u = User.objects.create_user(
                username=username,
                password="barber123",
                role=User.Role.BARBERO,
                first_name=first,
                last_name=last,
                phone="+591 70000002",
            )
            barber_users.append(u)
        # --- Estilista user ---
        estilista_user = User.objects.create_user(
            username="estilista",
            password="estilista123",
            role=User.Role.ESTILISTA,
            first_name="Sofia",
            last_name="Lopez",
            phone="+591 70000003",
        )
        self.stdout.write("  ✓ 1 estilista user (pass: estilista123)")

        # --- Employees ---
        employees = []
        emp_data = [
            (barber_users[0], "Carlos Mendoza", "12345678"),
            (barber_users[1], "Juan Perez", "23456789"),
            (barber_users[2], "Miguel Torres", "34567890"),
            (estilista_user, "Sofia Lopez", "90123456"),
        ]
        for user, full_name, doc in emp_data:
            e = Employee.objects.create(
                user=user,
                full_name=full_name,
                document_id=doc,
                phone="+591 70000002",
                email=full_name.lower().replace(" ", ".") + "@barberia.com",
                is_active=True,
            )
            employees.append(e)
        self.stdout.write("  ✓ 4 employees")

        # --- Clients ---
        client_data = [
            ("Roberto Flores", "45678901"),
            ("Ana Maria Lopez", "56789012"),
            ("Pedro Gutierrez", "67890123"),
            ("Lucia Fernandez", "78901234"),
            ("Diego Martinez", "89012345"),
        ]
        clients = [
            Client.objects.create(
                full_name=name,
                document_id=doc,
                phone="+591 70000002",
                birth_date=date(1990, 1, 1),
                is_active=True,
            )
            for name, doc in client_data
        ]
        self.stdout.write("  ✓ 5 clients")

        # --- Catalog ---
        services = [
            ("Corte de cabello", Decimal("50.00"), Decimal("40"), 30),
            ("Corte + Barba", Decimal("70.00"), Decimal("40"), 45),
            ("Barba completa", Decimal("30.00"), Decimal("50"), 20),
            ("Corte infantil", Decimal("40.00"), Decimal("40"), 30),
            ("Tinte completo", Decimal("150.00"), Decimal("30"), 90),
            ("Corte degradado", Decimal("60.00"), Decimal("40"), 40),
        ]
        products = [
            ("Gel fijador", Decimal("25.00"), 20),
            ("Cera modeladora", Decimal("35.00"), 15),
            ("Shampoo profesional", Decimal("45.00"), 10),
            ("Aceite para barba", Decimal("55.00"), 12),
        ]

        catalog_items = {}
        for name, price, comm, dur in services:
            item = CatalogItem.objects.create(
                kind=CatalogItem.Kind.SERVICE,
                name=name,
                description=name,
                price=price,
                barber_commission_percent=comm,
                duration_minutes=dur,
                current_stock=0,
                is_active=True,
            )
            catalog_items[name] = item

        for name, price, stock in products:
            item = CatalogItem.objects.create(
                kind=CatalogItem.Kind.PRODUCT,
                name=name,
                description=name,
                price=price,
                barber_commission_percent=Decimal("0"),
                current_stock=stock,
                is_active=True,
            )
            catalog_items[name] = item
        self.stdout.write("  ✓ 6 services + 4 products")

        # --- Sales for last N days ---
        statuses = [Sale.Status.DONE] * 4 + [Sale.Status.CANCELED]

        sale_count = 0
        for day_offset in range(days_back, 0, -1):
            day = now - timedelta(days=day_offset)
            num_sales = random.randint(3, 8)
            for _ in range(num_sales):
                is_service = random.random() < 0.7
                if is_service:
                    svc = random.choice(services)
                    product = catalog_items[svc[0]]
                    qty = 1
                else:
                    prod = random.choice(products)
                    product = catalog_items[prod[0]]
                    qty = random.randint(1, 3)

                employee = random.choice(employees)
                client = random.choice(clients) if random.random() < 0.6 else None
                status = random.choice(statuses)

                hour = random.randint(8, 19)
                minute = random.randint(0, 59)
                scheduled = day.replace(
                    hour=hour, minute=minute, second=0, microsecond=0
                )

                if status == Sale.Status.DONE:
                    completed = scheduled + timedelta(minutes=random.randint(15, 60))
                else:
                    completed = None

                commission_amount = None
                tip_amount = None
                if status == Sale.Status.DONE and is_service:
                    commission_amount = (
                        product.price
                        * product.barber_commission_percent
                        / Decimal("100")
                    ) * qty
                    tip_amount = Decimal(random.choice([0, 0, 0, 5, 10, 15, 20]))

                sale = Sale.objects.create(
                    client=client,
                    employee=employee,
                    product=product,
                    performed_by=employee.user,
                    scheduled_for=scheduled,
                    completed_at=completed,
                    status=status,
                    notes=(
                        ""
                        if status != Sale.Status.CANCELED
                        else "Cancelado por cliente"
                    ),
                    product_price=product.price,
                    quantity=qty,
                    commission_amount=commission_amount,
                    tip_amount=tip_amount,
                )
                sale_count += 1

                if status == Sale.Status.DONE and not is_service:
                    sale.refresh_from_db()
                    InventoryMovement.objects.create(
                        product=product,
                        quantity=-qty,
                        movement_type=InventoryMovement.MovementType.SALE,
                        unit_cost=product.price,
                        origen=sale.codigo,
                        notes=f"Venta #{sale.id}",
                        is_supply=False,
                        created_by=employee.user,
                    )

        self.stdout.write(f"  ✓ {sale_count} sales")

        # --- Purchases ---
        purchase_count = 0
        for prod_name, _, _ in products:
            item = catalog_items[prod_name]
            for _ in range(random.randint(1, 3)):
                qty = random.randint(5, 20)
                unit_cost = Decimal(str(random.randint(10, 40)))
                day_offset = random.randint(1, days_back)
                day = now - timedelta(days=day_offset)

                purchase = Purchase.objects.create(
                    product=item,
                    quantity=qty,
                    unit_cost=unit_cost,
                    notes="Compra de reposición",
                    created_by=admin_user,
                )
                purchase.refresh_from_db()
                purchase_count += 1

                InventoryMovement.objects.create(
                    product=item,
                    quantity=qty,
                    movement_type=InventoryMovement.MovementType.PURCHASE,
                    unit_cost=unit_cost,
                    origen=purchase.codigo,
                    notes="Compra de reposición",
                    is_supply=False,
                    created_by=admin_user,
                )

                item.current_stock += qty
                item.save()

        self.stdout.write(f"  ✓ {purchase_count} purchases")

        # --- Reset admin password ---
        if options["reset_admin"]:
            admin_user.set_password("admin123")
            admin_user.save()
            self.stdout.write("  ✓ Admin password reset: admin123")

        set_current_db_name(None)
        self.stdout.write(
            self.style.SUCCESS(f"\n✅ Seed completado para tenant '{tenant}'")
        )
        self.stdout.write("   admin / admin123")
        self.stdout.write("   carlos, juan, miguel / barber123")
        self.stdout.write("   estilista / estilista123")

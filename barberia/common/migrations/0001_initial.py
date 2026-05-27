from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Company",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("nit", models.CharField(max_length=30, unique=True)),
                ("name", models.CharField(max_length=200)),
            ],
            options={
                "verbose_name": "Empresa",
                "verbose_name_plural": "Empresas",
            },
        ),
    ]

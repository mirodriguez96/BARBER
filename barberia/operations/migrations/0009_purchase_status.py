from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("operations", "0008_purchase_is_active"),
    ]

    operations = [
        migrations.AddField(
            model_name="purchase",
            name="status",
            field=models.CharField(
                choices=[("active", "Activo"), ("canceled", "Anulado")],
                default="active",
                max_length=20,
            ),
        ),
        migrations.RunSQL(
            "UPDATE operations_purchase SET status='canceled' WHERE is_active=False",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RemoveField(
            model_name="purchase",
            name="is_active",
        ),
    ]

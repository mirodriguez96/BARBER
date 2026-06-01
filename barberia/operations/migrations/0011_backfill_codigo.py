from django.db import migrations


def backfill_codigo(apps, schema_editor):
    Sale = apps.get_model("operations", "Sale")
    Purchase = apps.get_model("operations", "Purchase")
    for sale in Sale.objects.iterator():
        Sale.objects.filter(pk=sale.pk).update(codigo=f"VEN-{sale.pk}")
    for purchase in Purchase.objects.iterator():
        Purchase.objects.filter(pk=purchase.pk).update(codigo=f"COM-{purchase.pk}")


class Migration(migrations.Migration):

    dependencies = [
        ("operations", "0010_purchase_codigo_sale_codigo"),
    ]

    operations = [
        migrations.RunPython(backfill_codigo, migrations.RunPython.noop),
    ]

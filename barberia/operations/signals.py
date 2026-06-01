from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Purchase, Sale


def _set_codigo(sender, instance, created, **kwargs):
    if created:
        prefix = "VEN" if sender is Sale else "COM"
        instance.codigo = f"{prefix}-{instance.pk}"
        sender.objects.filter(pk=instance.pk).update(codigo=instance.codigo)


@receiver(post_save, sender=Sale)
def sale_post_save(sender, instance, created, **kwargs):
    _set_codigo(sender, instance, created)


@receiver(post_save, sender=Purchase)
def purchase_post_save(sender, instance, created, **kwargs):
    _set_codigo(sender, instance, created)

from django.apps import AppConfig


class OperationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "barberia.operations"

    def ready(self):
        import barberia.operations.signals  # noqa

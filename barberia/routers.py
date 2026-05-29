import threading

from django.conf import settings

_thread_local = threading.local()


def get_current_db_name():
    return getattr(_thread_local, "tenant_db_name", None)


def set_current_db_name(db_name):
    _thread_local.tenant_db_name = db_name


class TenantRouter:
    route_app_labels = {"tenants", "axes"}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return "default"
        db_name = get_current_db_name()
        if db_name:
            return db_name
        return "default"

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return "default"
        db_name = get_current_db_name()
        if db_name:
            return db_name
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        if obj1._meta.app_label in self.route_app_labels or obj2._meta.app_label in self.route_app_labels:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == "default":
            return True
        if app_label in self.route_app_labels:
            return db == "default"
        return True

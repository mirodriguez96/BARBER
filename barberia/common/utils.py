from barberia.accounts.models import User
from barberia.dashboard.models import RoleCrudPermission


def _get_crud_allowed(user, app_key):
    if user.role == User.Role.ADMIN:
        return None
    return set(
        RoleCrudPermission.objects.filter(
            role=user.role,
            app_key=app_key,
        ).values_list("action", flat=True)
    )


def can_register(user, app_key):
    allowed = _get_crud_allowed(user, app_key)
    return allowed is None or RoleCrudPermission.Action.REGISTRAR in allowed


def can_modify(user, app_key):
    allowed = _get_crud_allowed(user, app_key)
    return allowed is None or RoleCrudPermission.Action.MODIFICAR in allowed


def can_deactivate(user, app_key):
    allowed = _get_crud_allowed(user, app_key)
    return allowed is None or RoleCrudPermission.Action.DESACTIVAR in allowed


def can_adjust(user, app_key):
    allowed = _get_crud_allowed(user, app_key)
    return allowed is None or RoleCrudPermission.Action.AJUSTAR in allowed

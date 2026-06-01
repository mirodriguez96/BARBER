from axes.backends import AxesStandaloneBackend
from django.contrib.auth.backends import ModelBackend


class SafeAxesBackend(AxesStandaloneBackend):
    def user_can_authenticate(self, user):
        is_active = getattr(user, "is_active", None)
        return is_active or is_active is None

    def get_user(self, user_id):
        return ModelBackend.get_user(self, user_id)

    def authenticate(self, request, username=None, password=None, **kwargs):
        if request is None:
            return ModelBackend.authenticate(
                self, request, username=username, password=password, **kwargs
            )

        result = super().authenticate(
            request, username=username, password=password, **kwargs
        )

        if result is None:
            return ModelBackend.authenticate(
                self, request, username=username, password=password, **kwargs
            )

        return result

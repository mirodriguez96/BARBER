from axes.backends import AxesStandaloneBackend
from django.contrib.auth.backends import ModelBackend


class SafeAxesBackend(AxesStandaloneBackend):
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

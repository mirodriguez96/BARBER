from axes.backends import AxesStandaloneBackend
from django.contrib.auth.backends import ModelBackend


class SafeAxesBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if request is None:
            return super().authenticate(
                request, username=username, password=password, **kwargs
            )

        axes_backend = AxesStandaloneBackend()

        result = axes_backend.authenticate(
            request, username=username, password=password, **kwargs
        )

        if result is None:
            return super().authenticate(
                request, username=username, password=password, **kwargs
            )

        return result

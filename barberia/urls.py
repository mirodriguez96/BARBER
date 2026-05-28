from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import include, path, reverse_lazy

from barberia.common import views as common_views

urlpatterns = [
    path("", common_views.BarberiaLoginView.as_view(), name="home"),
    path("login/", common_views.BarberiaLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(next_page=reverse_lazy("login")), name="logout"),
    path("admin/", admin.site.urls),
    path("dashboard/", include("barberia.dashboard.urls")),
    path("accounts/", include("barberia.accounts.urls")),
    path("tenants/", include("barberia.tenants.urls")),
]

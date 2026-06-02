from django.urls import path

from . import views

app_name = "booking"
urlpatterns = [
    path("", views.service_list, name="service_list"),
    path("api/client/", views.api_client_lookup, name="api_client_lookup"),
    path("api/barbers/<str:date_str>/", views.api_barbers, name="api_barbers"),
    path("api/slots/<int:service_id>/<str:date_str>/", views.api_slots, name="api_slots"),
    path("<int:service_id>/", views.booking_form, name="booking_form"),
    path("<int:service_id>/confirm/", views.booking_confirm, name="booking_confirm"),
    path("<int:sale_id>/done/", views.booking_done, name="booking_done"),
]

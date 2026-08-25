"""Routes for the public website."""

from django.urls import path

from web.views import (
    HomeView,
    ReservationConfirmationView,
    ReservationLookupView,
    ReservationPageView,
)

app_name = "web"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("reservaciones/", ReservationPageView.as_view(), name="reservations"),
    path(
        "reservaciones/confirmacion/<str:code>/",
        ReservationConfirmationView.as_view(),
        name="reservation-confirmation",
    ),
    path(
        "reservaciones/consultar/",
        ReservationLookupView.as_view(),
        name="reservation-lookup",
    ),
]

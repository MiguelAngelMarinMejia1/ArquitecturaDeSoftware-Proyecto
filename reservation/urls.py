from django.urls import path

from reservation.views import CrearReservaView, ReservaConfirmadaView

app_name = "reservation"

urlpatterns = [
    path("crear/", CrearReservaView.as_view(), name="crear_reserva"),
    path("confirmada/<int:pk>/", ReservaConfirmadaView.as_view(), name="reserva_confirmada"),
]

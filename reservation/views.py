"""
views.py
Capa de Interfaz (Django View)

Responsabilidad única: leer el request, delegar al Service y renderizar.
Nada de validaciones de negocio ni cálculos de precio aquí.
"""
from datetime import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import DetailView

from reservation.models import Habitacion, Reserva
from reservation.domain.exceptions import ReservationDomainError
from reservation.services import ReservaService


class CrearReservaView(LoginRequiredMixin, View):
    template_name = "reservation/crear_reserva.html"

    def get(self, request):
        habitaciones = Habitacion.objects.filter(activa=True).select_related("hotel")
        return render(request, self.template_name, {"habitaciones": habitaciones})

    def post(self, request):
        habitaciones = Habitacion.objects.filter(activa=True).select_related("hotel")
        try:
            datos = {
                "habitacion_id": request.POST.get("habitacion"),
                "fecha_entrada": datetime.strptime(request.POST["fecha_entrada"], "%Y-%m-%d").date(),
                "fecha_salida": datetime.strptime(request.POST["fecha_salida"], "%Y-%m-%d").date(),
                "num_huespedes": int(request.POST.get("num_huespedes", 1)),
                "solicitudes_especiales": request.POST.get("solicitudes_especiales", ""),
            }
            reserva = ReservaService().crear_reserva(request.user, datos)
        except (
            ValidationError,
            ValueError,
            KeyError,
            Habitacion.DoesNotExist,
            ReservationDomainError,
        ) as e:
            mensaje = str(e) or "Revisa los datos del formulario."
            return render(request, self.template_name, {
                "habitaciones": habitaciones,
                "error": mensaje,
                "datos": request.POST,
            })
        return redirect("reservation:reserva_confirmada", pk=reserva.pk)


class ReservaConfirmadaView(LoginRequiredMixin, DetailView):
    model = Reserva
    template_name = "reservation/reserva_confirmada.html"
    context_object_name = "reserva"
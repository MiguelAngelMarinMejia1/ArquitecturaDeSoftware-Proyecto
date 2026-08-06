# reservation/domain/builders.py
"""Builder for the Reservation entity.

Responsibility: assemble a Reserva step by step (Fluent Interface) and
guarantee it is valid BEFORE it touches the database. This builder does NOT
calculate prices or handle state transitions (confirm/cancel) — those belong
to ReservaService.
"""

from reservation.models import Habitacion, Reserva
from reservation.domain.exceptions import (
    IncompleteReservationDataError,
    InvalidDateRangeError,
    RoomNotAvailableError,
    GuestCapacityExceededError,
)


class ReservaBuilder:
    """Fluent builder that accumulates reservation data and validates it
    before persisting."""

    _MAX_HUESPEDES_POR_TIPO = {
        Habitacion.Tipo.SENCILLA: 1,
        Habitacion.Tipo.DOBLE: 2,
        Habitacion.Tipo.SUITE: 4,
    }

    def __init__(self):
        self._usuario = None
        self._habitacion = None
        self._fecha_entrada = None
        self._fecha_salida = None
        self._num_huespedes = None
        self._solicitudes_especiales = ""

    def para_usuario(self, usuario):
        self._usuario = usuario
        return self

    def para_habitacion(self, habitacion):
        self._habitacion = habitacion
        return self

    def con_fechas(self, fecha_entrada, fecha_salida):
        self._fecha_entrada = fecha_entrada
        self._fecha_salida = fecha_salida
        return self

    def con_huespedes(self, num_huespedes):
        self._num_huespedes = num_huespedes
        return self

    def con_solicitudes(self, solicitudes_especiales):
        self._solicitudes_especiales = solicitudes_especiales or ""
        return self

    def build(self) -> Reserva:
        self._validate_completeness()
        self._validate_date_range()
        self._validate_guest_capacity()
        self._validate_room_availability()

        reserva = Reserva.objects.create(
            usuario=self._usuario,
            habitacion=self._habitacion,
            fechaEntrada=self._fecha_entrada,
            fechaSalida=self._fecha_salida,
            numHuespedes=self._num_huespedes,
            solicitudesEspeciales=self._solicitudes_especiales,
        )
        return reserva

    # --- Internal validation steps -----------------------------------

    def _validate_completeness(self):
        missing = [
            name for name, value in [
                ("usuario", self._usuario),
                ("habitacion", self._habitacion),
                ("fecha_entrada", self._fecha_entrada),
                ("fecha_salida", self._fecha_salida),
                ("num_huespedes", self._num_huespedes),
            ] if value is None
        ]
        if missing:
            raise IncompleteReservationDataError(
                f"Faltan datos requeridos de reserva: {', '.join(missing)}"
            )

    def _validate_date_range(self):
        if self._fecha_entrada >= self._fecha_salida:
            raise InvalidDateRangeError(
                "fecha_entrada debe ser anterior a fecha_salida."
            )

    def _validate_guest_capacity(self):
        max_capacity = self._MAX_HUESPEDES_POR_TIPO.get(
            self._habitacion.tipo,
            self._num_huespedes,
        )
        if self._num_huespedes > max_capacity:
            raise GuestCapacityExceededError(
                f"La habitación '{self._habitacion}' admite hasta {max_capacity} "
                f"huespedes, pero se solicitaron {self._num_huespedes}."
            )

    def _validate_room_availability(self):
        if not self._habitacion.esta_disponible(
            self._fecha_entrada,
            self._fecha_salida,
        ):
            raise RoomNotAvailableError(
                f"La habitación {self._habitacion.numero} no está disponible "
                f"entre {self._fecha_entrada} y {self._fecha_salida}."
            )

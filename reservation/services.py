"""Application service layer for reservation orchestration."""

from reservation.domain.builders import ReservaBuilder
from reservation.infra.factories import NotifierFactory
from reservation.models import Habitacion


class ReservaService:
    """Orquesta la creación de reservas y el envío de notificaciones."""

    def __init__(self, notifier_type=None):
        self.notifier = NotifierFactory.create(notifier_type)

    def crear_reserva(self, usuario, datos):
        """Crea una reserva usando el builder y notifica al usuario."""
        habitacion = Habitacion.objects.get(pk=datos["habitacion_id"])

        reserva = (
            ReservaBuilder()
            .para_usuario(usuario)
            .para_habitacion(habitacion)
            .con_fechas(datos["fecha_entrada"], datos["fecha_salida"])
            .con_huespedes(datos["num_huespedes"])
            .con_solicitudes(datos.get("solicitudes_especiales", ""))
            .build()
        )

        self.notifier.send_confirmation(reserva)
        return reserva

    def crear_reserva_con_notificador(self, usuario, datos, notifier_type):
        """Crea una reserva y permite elegir un notificador explícito."""
        self.notifier = NotifierFactory.create(notifier_type)
        return self.crear_reserva(usuario, datos)

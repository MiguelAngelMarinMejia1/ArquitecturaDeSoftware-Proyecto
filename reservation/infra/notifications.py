"""Notification adapters.

Infrastructure detail: the application layer depends on the ``BaseNotifier``
abstraction and never on a concrete class, which is what allows the notifier to
be swapped per environment (console in development, e-mail in production,
the Flask notification microservice inside Docker) without a single change in
``services.py``.
"""

import logging
from abc import ABC, abstractmethod

import requests
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


class BaseNotifier(ABC):
    """Contract every notification channel must satisfy."""

    @abstractmethod
    def send_confirmation(self, reservation) -> bool:
        """Notify the guest that their reservation was created."""
        raise NotImplementedError


class ConsoleNotifier(BaseNotifier):
    """Development notifier: prints the confirmation instead of sending it.

    Keeps local development free of SMTP configuration while exercising exactly
    the same code path as production.
    """

    def send_confirmation(self, reservation) -> bool:
        print(
            f"[DEV] Reserva {reservation.confirmation_code} creada para "
            f"{reservation.customer} ({reservation.customer.email}). "
            f"Entrada {reservation.check_in_date}, salida {reservation.check_out_date}. "
            f"Total {reservation.total_amount}."
        )
        return True


class EmailNotifier(BaseNotifier):
    """Production notifier backed by Django's e-mail machinery.

    Failures are swallowed on purpose: a reservation that is already committed
    must not be rolled back because the confirmation e-mail bounced. The
    delivery problem is reported by the return value instead.
    """

    def send_confirmation(self, reservation) -> bool:
        subject = f"Hotel MDJ - Reserva {reservation.confirmation_code}"
        body = (
            f"Hola {reservation.customer.first_name},\n\n"
            f"Tu reserva {reservation.confirmation_code} quedo registrada.\n"
            f"Entrada: {reservation.check_in_date}\n"
            f"Salida: {reservation.check_out_date}\n"
            f"Total: {reservation.total_amount}\n\n"
            "Hotel MDJ"
        )
        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=None,
                recipient_list=[reservation.customer.email],
                fail_silently=False,
            )
            return True
        except Exception as exc:  # pragma: no cover - depends on SMTP backend
            print(f"[EMAIL] No se pudo enviar la confirmacion: {exc}")
            return False


class HttpNotifier(BaseNotifier):
    """Adapter to the Flask notification microservice (``notification_service/``).

    Publishes a ``RESERVATION_CONFIRMED`` event. Like ``EmailNotifier``, it
    never raises: the booking is already committed when this runs, so a
    service outage is logged and reported through the return value only.
    """

    EVENT = "RESERVATION_CONFIRMED"

    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        self._url = (base_url or settings.NOTIFICATION_SERVICE_URL).rstrip("/") + "/"
        self._timeout = timeout or settings.MICROSERVICE_TIMEOUT

    def send_confirmation(self, reservation) -> bool:
        payload = {
            "event": self.EVENT,
            "confirmation_code": reservation.confirmation_code,
            "recipient_email": reservation.customer.email,
            "recipient_name": reservation.customer.first_name,
            "check_in_date": reservation.check_in_date.isoformat(),
            "check_out_date": reservation.check_out_date.isoformat(),
            "total_amount": str(reservation.total_amount),
        }
        try:
            response = requests.post(
                self._url,
                json=payload,
                headers={"X-Internal-Token": settings.INTERNAL_API_TOKEN},
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            logger.error("Notification service unreachable at %s: %s", self._url, exc)
            return False

        if response.status_code != 201:
            logger.error(
                "Notification for %s not sent (%s): %s",
                reservation.confirmation_code,
                response.status_code,
                response.text[:300],
            )
            return False
        return True


class CeleryNotifier(BaseNotifier):
    """Queues the confirmation in Redis for the Celery worker.

    The request only pays for publishing a message. The worker delivers it
    later through ``settings.NOTIFIER_DELIVERY_TYPE`` (the Flask service by
    default) and retries while delivery fails.

    If the broker itself is unreachable the notification is delivered
    synchronously instead, so the guest is never left without one.
    """

    def send_confirmation(self, reservation) -> bool:
        from reservation.tasks import send_reservation_confirmation

        try:
            send_reservation_confirmation.delay(reservation.pk)
            return True
        except Exception as exc:  # kombu raises several connection errors
            logger.error(
                "Broker unavailable, notifying %s synchronously: %s",
                reservation.confirmation_code,
                exc,
            )
            from reservation.infra.factories import NotifierFactory

            fallback = NotifierFactory.create(settings.NOTIFIER_DELIVERY_TYPE)
            return fallback.send_confirmation(reservation)

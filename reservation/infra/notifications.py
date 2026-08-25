"""Notification adapters.

Infrastructure detail: the application layer depends on the ``BaseNotifier``
abstraction and never on a concrete class, which is what allows the notifier to
be swapped per environment (console in development, e-mail in production)
without a single change in ``services.py``.
"""

from abc import ABC, abstractmethod

from django.core.mail import send_mail


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

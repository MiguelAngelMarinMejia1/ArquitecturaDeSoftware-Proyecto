"""Notification implementations.

These classes represent infrastructure services. The application does not need
to know which implementation is being used.
"""

from abc import ABC, abstractmethod


class BaseNotifier(ABC):
    """Abstract notification contract."""

    @abstractmethod
    def send_confirmation(self, reservation):
        raise NotImplementedError


class ConsoleNotifier(BaseNotifier):
    """Development notifier that prints to the console."""

    def send_confirmation(self, reservation):
        print(
            f"[DEV] Reservation {reservation.id} confirmed for "
            f"{reservation.customer}."
        )


class EmailNotifier(BaseNotifier):
    """Production notifier placeholder."""

    def send_confirmation(self, reservation):
        # Replace this with Django's email backend later.
        print(
            f"[EMAIL] Confirmation email sent to "
            f"{reservation.customer}."
        )
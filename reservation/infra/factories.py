"""Creational factories for infrastructure dependencies.

Why a Factory here? The service layer needs *a* notifier and *a* payment
gateway, but choosing which concrete implementation to build is an
infrastructure decision that depends on configuration, not on business rules.
Putting that decision inside the services would hard-wire them to a specific
class and force an edit every time a new channel or provider appears.

Each factory therefore owns one thing: translating a configuration value into
the right object. Adding a provider means adding a branch here and a class in
the adapter module -- no service, view or serializer changes.
"""

from django.conf import settings

from reservation.infra.notifications import (
    BaseNotifier,
    ConsoleNotifier,
    EmailNotifier,
)
from reservation.infra.payments import BaseGateway, SimulatedGateway


class NotifierFactory:
    """Builds the notification channel configured for this environment."""

    CONSOLE = "CONSOLE"
    EMAIL = "EMAIL"

    _REGISTRY = {
        CONSOLE: ConsoleNotifier,
        EMAIL: EmailNotifier,
    }

    @classmethod
    def create(cls, notifier_type: str | None = None) -> BaseNotifier:
        key = (notifier_type or getattr(settings, "NOTIFIER_TYPE", cls.CONSOLE)).upper()
        # Falls back to the console channel: an unknown value must never leave
        # the guest without any notification at all.
        notifier_class = cls._REGISTRY.get(key, ConsoleNotifier)
        return notifier_class()


class PaymentGatewayFactory:
    """Builds the payment gateway configured for this environment."""

    SIMULATED = "SIMULATED"

    _REGISTRY = {
        SIMULATED: SimulatedGateway,
    }

    @classmethod
    def create(cls, gateway_type: str | None = None) -> BaseGateway:
        key = (
            gateway_type or getattr(settings, "PAYMENT_GATEWAY_TYPE", cls.SIMULATED)
        ).upper()
        gateway_class = cls._REGISTRY.get(key)
        if gateway_class is None:
            raise ValueError(
                f"Pasarela de pago no soportada: '{key}'. "
                f"Opciones validas: {', '.join(sorted(cls._REGISTRY))}."
            )
        return gateway_class()

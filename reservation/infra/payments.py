"""Payment gateway adapters.

The service layer charges a ``BaseGateway`` and never learns which
implementation answered:

* ``SimulatedGateway``: in-process, for running Django alone.
* ``HttpPaymentGateway``: adapter to the Flask payment microservice
  (``payment_service/``), reached through the Nginx gateway. This is the
  default inside Docker (Strangler Pattern).
"""

import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChargeResult:
    """Outcome of a charge attempt, in gateway-agnostic terms."""

    approved: bool
    reference: str
    message: str = ""


class BaseGateway(ABC):
    """Contract every payment provider adapter must satisfy."""

    @abstractmethod
    def charge(self, amount: Decimal, method: str, reference_hint: str = "") -> ChargeResult:
        """Attempt to collect ``amount`` and report the outcome."""
        raise NotImplementedError


class SimulatedGateway(BaseGateway):
    """Development gateway that approves every charge.

    Stands in until a provider is selected. It captures no card data by
    design: accepting real card numbers would bring the whole application into
    PCI-DSS scope, and nothing in the booking flow needs them to work.
    """

    PROVIDER = "SIMULATED"

    def charge(self, amount: Decimal, method: str, reference_hint: str = "") -> ChargeResult:
        reference = f"{self.PROVIDER}-{uuid.uuid4().hex[:12].upper()}"
        return ChargeResult(
            approved=True,
            reference=reference,
            message=(
                f"Cobro simulado de {amount} aprobado "
                f"(metodo {method}, referencia {reference_hint or 'n/a'})."
            ),
        )


class HttpPaymentGateway(BaseGateway):
    """Adapter: translates ``BaseGateway.charge`` into a call to the payment
    microservice and its JSON answer back into a ``ChargeResult``.

    Any network failure or unexpected answer becomes a *declined* charge, so
    ``PaymentService`` raises ``PaymentDeclinedError`` and the reservation
    transaction rolls back: no booking is ever confirmed without a payment.
    """

    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        self._url = (base_url or settings.PAYMENT_SERVICE_URL).rstrip("/") + "/"
        self._timeout = timeout or settings.MICROSERVICE_TIMEOUT

    def charge(self, amount: Decimal, method: str, reference_hint: str = "") -> ChargeResult:
        try:
            response = requests.post(
                self._url,
                json={
                    "amount": str(amount),
                    "method": method,
                    "reference_hint": reference_hint,
                },
                timeout=self._timeout,
            )
            body = response.json()
        except (requests.RequestException, ValueError) as exc:
            logger.error("Payment service unreachable at %s: %s", self._url, exc)
            return ChargeResult(
                approved=False,
                reference="",
                message=(
                    "El servicio de pagos no está disponible en este momento. "
                    "No se realizó ningún cobro, intenta de nuevo en unos minutos."
                ),
            )

        if response.status_code in (201, 402) and "reference" in body:
            return ChargeResult(
                approved=bool(body.get("approved")),
                reference=body["reference"],
                message=body.get("message", ""),
            )

        detail = (body.get("error") or {}).get("detail", "Respuesta inesperada.")
        logger.error("Payment service answered %s: %s", response.status_code, body)
        return ChargeResult(approved=False, reference="", message=str(detail))

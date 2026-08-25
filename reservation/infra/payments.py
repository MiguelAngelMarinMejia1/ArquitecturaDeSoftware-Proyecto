"""Payment gateway adapters.

Only a simulated gateway exists today. It is still modelled behind an
abstraction because that is the seam a real provider (PayU, Wompi, Stripe)
would plug into: the service layer charges a ``BaseGateway`` and never learns
which provider answered.
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


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

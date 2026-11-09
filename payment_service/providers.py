"""Payment providers this service can charge through.

Moved here from ``reservation/infra/payments.py``: the monolith no longer
talks to any provider, it only calls this service.
"""

import uuid


class SimulatedProvider:
    """Approves every charge. Captures no card data (keeps us out of PCI-DSS)."""

    NAME = "SIMULATED"

    def charge(self, amount, method, reference_hint=""):
        reference = f"{self.NAME}-{uuid.uuid4().hex[:12].upper()}"
        message = (
            f"Cobro simulado de {amount} aprobado "
            f"(método {method}, referencia {reference_hint or 'n/a'})."
        )
        return True, reference, message


_PROVIDERS = {SimulatedProvider.NAME: SimulatedProvider}


def build_provider(name):
    provider_class = _PROVIDERS.get((name or "").upper())
    if provider_class is None:
        raise ValueError(
            f"Proveedor de pagos no soportado: '{name}'. "
            f"Opciones válidas: {', '.join(sorted(_PROVIDERS))}."
        )
    return provider_class()

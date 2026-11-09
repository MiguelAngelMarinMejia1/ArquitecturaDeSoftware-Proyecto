"""Validation of the charge request body.

    {
        "amount": "642600.00",
        "method": "CREDIT_CARD",
        "reference_hint": "MDJ-7KQ2M9XD"
    }
"""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from errors import InvalidAmountError, InvalidMethodError, InvalidPayloadError

# Same choices as Payment.Method in the Django monolith.
ALLOWED_METHODS = ("CREDIT_CARD", "DEBIT_CARD", "CASH", "TRANSFER")


def parse_charge_request(payload):
    if not isinstance(payload, dict):
        raise InvalidPayloadError("El cuerpo de la petición debe ser un objeto JSON.")

    return {
        "amount": _parse_amount(payload.get("amount")),
        "method": _parse_method(payload.get("method")),
        "reference_hint": _parse_reference_hint(payload.get("reference_hint", "")),
    }


def _parse_amount(raw):
    if isinstance(raw, bool) or not isinstance(raw, (int, float, str)):
        raise InvalidAmountError("El campo 'amount' es obligatorio y debe ser numérico.")
    try:
        amount = Decimal(str(raw))
    except InvalidOperation:
        raise InvalidAmountError(f"El monto '{raw}' no es un número válido.")
    if not amount.is_finite() or amount <= 0:
        raise InvalidAmountError("El monto debe ser mayor que 0.")
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _parse_method(raw):
    if raw not in ALLOWED_METHODS:
        raise InvalidMethodError(
            f"Método de pago no soportado: '{raw}'. "
            f"Opciones válidas: {', '.join(ALLOWED_METHODS)}."
        )
    return raw


def _parse_reference_hint(raw):
    if not isinstance(raw, str) or len(raw) > 40:
        raise InvalidPayloadError(
            "El campo 'reference_hint' debe ser un texto de máximo 40 caracteres."
        )
    return raw.strip()

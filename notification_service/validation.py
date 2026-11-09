"""Validation of the notification event body.

    {
        "event": "RESERVATION_CONFIRMED",
        "confirmation_code": "MDJ-7KQ2M9XD",
        "recipient_email": "ana@example.com",
        "recipient_name": "Ana",
        "check_in_date": "2026-12-10",
        "check_out_date": "2026-12-13",
        "total_amount": "642600.00"
    }
"""

import re
from datetime import date

from errors import InvalidPayloadError

SUPPORTED_EVENTS = ("RESERVATION_CONFIRMED",)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _required_text(payload, name, max_length):
    value = payload.get(name)
    if not isinstance(value, str) or not value.strip():
        raise InvalidPayloadError(f"El campo '{name}' es obligatorio.")
    if len(value) > max_length:
        raise InvalidPayloadError(f"El campo '{name}' supera {max_length} caracteres.")
    return value.strip()


def _required_date(payload, name):
    value = _required_text(payload, name, 10)
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        raise InvalidPayloadError(f"El campo '{name}' debe tener formato AAAA-MM-DD.")


def parse_notification_request(payload):
    if not isinstance(payload, dict):
        raise InvalidPayloadError("El cuerpo de la petición debe ser un objeto JSON.")

    event = payload.get("event")
    if event not in SUPPORTED_EVENTS:
        raise InvalidPayloadError(
            f"Evento no soportado: '{event}'. Opciones: {', '.join(SUPPORTED_EVENTS)}."
        )

    email = _required_text(payload, "recipient_email", 254)
    if not _EMAIL_RE.match(email):
        raise InvalidPayloadError("El campo 'recipient_email' no es un correo válido.")

    return {
        "event": event,
        "confirmation_code": _required_text(payload, "confirmation_code", 20),
        "recipient_email": email,
        "recipient_name": _required_text(payload, "recipient_name", 100),
        "check_in_date": _required_date(payload, "check_in_date"),
        "check_out_date": _required_date(payload, "check_out_date"),
        "total_amount": _required_text(payload, "total_amount", 20),
    }

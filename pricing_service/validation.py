"""Validation of the quote request body.

Checks every field, converts it to a Python type (date, Decimal, int) and
raises an error from ``errors.py`` (-> 400) when something is wrong.

Expected body:

    {
        "check_in_date": "2026-10-10",
        "check_out_date": "2026-10-13",
        "rooms": [
            {"room_id": 1, "price_per_night": "180000.00"},
            {"room_id": 5, "price_per_night": 250000}
        ]
    }

One small function per rule: to add or change a rule, edit only that function.
"""

from datetime import date
from decimal import Decimal, InvalidOperation

from errors import (
    InvalidDateRangeError,
    InvalidPayloadError,
    InvalidPriceError,
    NoRoomsSelectedError,
)


def parse_quote_request(payload, today):
    """Validate the whole body and return clean values.

    ``today`` is a parameter so the caller picks the time zone and tests can
    use a fixed date.
    """
    if not isinstance(payload, dict):
        raise InvalidPayloadError("El cuerpo de la peticion debe ser un objeto JSON.")

    check_in = parse_date(payload, "check_in_date")
    check_out = parse_date(payload, "check_out_date")
    validate_date_range(check_in, check_out, today)

    rooms = parse_rooms(payload.get("rooms"))

    return {
        "check_in": check_in,
        "check_out": check_out,
        "rooms": rooms,
    }


# --- Dates ----------------------------------------------------------------


def parse_date(payload, field_name):
    """Required date in ISO format (YYYY-MM-DD)."""
    value = payload.get(field_name)

    if value is None:
        raise InvalidPayloadError(f"El campo '{field_name}' es obligatorio.")
    if not isinstance(value, str):
        raise InvalidPayloadError(
            f"El campo '{field_name}' debe ser un texto con formato AAAA-MM-DD."
        )

    try:
        return date.fromisoformat(value)
    except ValueError:
        raise InvalidPayloadError(
            f"El campo '{field_name}' debe tener formato AAAA-MM-DD, "
            f"se recibio '{value}'."
        )


def validate_date_range(check_in, check_out, today):
    """Same date rules as Django's ReservationBuilder."""
    if check_out <= check_in:
        raise InvalidDateRangeError(
            "La fecha de salida debe ser posterior a la fecha de entrada."
        )
    if check_in < today:
        raise InvalidDateRangeError(
            "La fecha de entrada no puede estar en el pasado."
        )


# --- Rooms ----------------------------------------------------------------


def parse_rooms(rooms):
    """List of rooms to quote; at least one, no repeated ids."""
    if rooms is None or rooms == []:
        raise NoRoomsSelectedError(
            "La cotizacion debe incluir al menos una habitacion."
        )
    if not isinstance(rooms, list):
        raise InvalidPayloadError("El campo 'rooms' debe ser una lista.")

    clean_rooms = []
    seen_ids = set()

    for position, room in enumerate(rooms, start=1):
        if not isinstance(room, dict):
            raise InvalidPayloadError(
                f"La habitacion #{position} debe ser un objeto con "
                f"'room_id' y 'price_per_night'."
            )

        room_id = parse_room_id(room, position)
        if room_id in seen_ids:
            raise InvalidPayloadError(
                f"La habitacion con id {room_id} esta repetida."
            )
        seen_ids.add(room_id)

        clean_rooms.append(
            {
                "room_id": room_id,
                "price_per_night": parse_price(room, position),
            }
        )

    return clean_rooms


def parse_room_id(room, position):
    """Whole number; JSON true/false are rejected."""
    room_id = room.get("room_id")

    if isinstance(room_id, bool) or not isinstance(room_id, int):
        raise InvalidPayloadError(
            f"La habitacion #{position} necesita un 'room_id' numerico entero."
        )
    return room_id


def parse_price(room, position):
    """Number or numeric string, greater than 0.

    Converted through ``str`` so 180000.1 becomes exactly Decimal("180000.1").
    """
    raw_price = room.get("price_per_night")

    if isinstance(raw_price, bool) or not isinstance(raw_price, (int, float, str)):
        raise InvalidPriceError(
            f"La habitacion #{position} necesita un 'price_per_night' numerico."
        )

    try:
        price = Decimal(str(raw_price))
    except InvalidOperation:
        raise InvalidPriceError(
            f"El 'price_per_night' de la habitacion #{position} no es un numero "
            f"valido: '{raw_price}'."
        )

    # is_finite() rejects "NaN" and "Infinity", which Decimal accepts as text.
    if not price.is_finite() or price <= 0:
        raise InvalidPriceError(
            f"El 'price_per_night' de la habitacion #{position} debe ser mayor que 0."
        )
    return price

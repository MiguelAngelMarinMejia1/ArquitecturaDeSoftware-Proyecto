"""Validation of the availability query string.

Same rules as Django's ``AvailabilityQuerySerializer``: check_in and
check_out required (YYYY-MM-DD), check_out after check_in, adults >= 1,
children >= 0, optional room_type id.
"""

from datetime import date

from errors import InvalidDateRangeError, InvalidQueryError


def _parse_date(args, name):
    value = args.get(name)
    if not value:
        raise InvalidQueryError({name: ["Este campo es requerido."]})
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise InvalidQueryError(
            {name: [f"Formato de fecha inválido, use AAAA-MM-DD. Se recibió '{value}'."]}
        )


def _parse_int(args, name, default, minimum):
    raw = args.get(name)
    if raw in (None, ""):
        return default
    try:
        value = int(raw)
    except ValueError:
        raise InvalidQueryError({name: ["Se requiere un número entero válido."]})
    if value < minimum:
        raise InvalidQueryError(
            {name: [f"Asegúrese de que este valor es mayor o igual a {minimum}."]}
        )
    return value


def parse_availability_query(args):
    check_in = _parse_date(args, "check_in")
    check_out = _parse_date(args, "check_out")
    if check_out <= check_in:
        raise InvalidDateRangeError(
            {"check_out": ["La fecha de salida debe ser posterior a la de entrada."]}
        )

    adults = _parse_int(args, "adults", default=1, minimum=1)
    children = _parse_int(args, "children", default=0, minimum=0)
    room_type = args.get("room_type")
    room_type_id = None
    if room_type not in (None, ""):
        room_type_id = _parse_int(args, "room_type", default=None, minimum=1)

    return {
        "check_in": check_in,
        "check_out": check_out,
        "guests": adults + children,
        "room_type_id": room_type_id,
    }


def parse_pagination_query(args, max_page_size=12):
    page = _parse_int(args, "page", default=1, minimum=1)
    page_size = _parse_int(args, "page_size", default=max_page_size, minimum=1)
    return page, min(page_size, max_page_size)

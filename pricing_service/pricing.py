"""Pricing rules of Hotel MDJ, extracted from the Django monolith.

These functions are a port of ``reservation/domain/policies.py``
(``PricingPolicy``, ``SeasonalPricingPolicy`` and ``TaxPolicy``). The math is
identical, so a quote from ``/api/v2/cotizacion/`` matches what Django charges.

Rules kept from the original:
* Money is always ``Decimal``, never ``float`` (float cannot store 0.1 exactly).
* Amounts are rounded to 2 decimals with ROUND_HALF_UP.
* Nights = check-out minus check-in (the check-out day is not charged).

Nothing here knows about Flask or HTTP: these are plain functions that can be
reused or tested on their own.
"""

from decimal import Decimal, ROUND_HALF_UP

CENTS = Decimal("0.01")


def to_money(value):
    """Round an amount to two decimal places (e.g. 10.005 -> 10.01)."""
    return Decimal(value).quantize(CENTS, rounding=ROUND_HALF_UP)


def count_nights(check_in, check_out):
    """Billable nights between two dates. Assumes the range is already valid."""
    return (check_out - check_in).days


def nightly_rate(base_price, on_date):
    """Rate charged for one night.

    The hotel has no seasons yet, so the base price applies every day. This is
    the one place to change if high/low season prices are ever added: for
    example, return ``base_price * Decimal("1.20")`` for December dates.
    """
    return to_money(base_price)


def calculate_taxes(subtotal, tax_rate):
    """Tax owed for a subtotal (tax_rate 0.19 means 19 %)."""
    return to_money(Decimal(subtotal) * Decimal(tax_rate))


def build_quote(rooms, check_in, check_out, tax_rate):
    """Price a stay for a list of rooms.

    ``rooms`` is a list of dicts: ``{"room_id": 1, "price_per_night": Decimal}``.
    Returns a plain dict ready to be sent as JSON (amounts as strings so no
    precision is lost on the way).
    """
    nights = count_nights(check_in, check_out)

    room_lines = []
    subtotal = Decimal("0.00")

    for room in rooms:
        rate = nightly_rate(room["price_per_night"], check_in)
        line_total = to_money(rate * nights)
        subtotal += line_total

        room_lines.append(
            {
                "room_id": room["room_id"],
                "price_per_night": str(rate),
                "nights": nights,
                "line_total": str(line_total),
            }
        )

    subtotal = to_money(subtotal)
    taxes = calculate_taxes(subtotal, tax_rate)
    total = to_money(subtotal + taxes)

    return {
        "check_in_date": check_in.isoformat(),
        "check_out_date": check_out.isoformat(),
        "nights": nights,
        "rooms": room_lines,
        "subtotal": str(subtotal),
        "tax_rate": str(tax_rate),
        "taxes": str(taxes),
        "total": str(total),
    }

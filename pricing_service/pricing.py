"""Pricing rules of Hotel MDJ, ported from the Django monolith.

Same math as ``reservation/domain/policies.py`` (PricingPolicy,
SeasonalPricingPolicy, TaxPolicy), so quotes match what Django charges:
* money is always Decimal, never float
* amounts are rounded to 2 decimals with ROUND_HALF_UP
* nights = check-out minus check-in

Plain functions with no Flask or HTTP, easy to reuse and test.
"""

from decimal import Decimal, ROUND_HALF_UP

CENTS = Decimal("0.01")


def to_money(value):
    """Round to two decimals (10.005 -> 10.01)."""
    return Decimal(value).quantize(CENTS, rounding=ROUND_HALF_UP)


def count_nights(check_in, check_out):
    """Billable nights. Assumes a valid range."""
    return (check_out - check_in).days


def nightly_rate(base_price, on_date):
    """Rate for one night. No seasons yet, so the base price always applies.

    Add seasonal prices here, e.g. ``base_price * Decimal("1.20")`` in December.
    """
    return to_money(base_price)


def calculate_taxes(subtotal, tax_rate):
    """Tax owed for a subtotal (0.19 = 19 %)."""
    return to_money(Decimal(subtotal) * Decimal(tax_rate))


def build_quote(rooms, check_in, check_out, tax_rate):
    """Price a stay.

    ``rooms``: list of ``{"room_id": int, "price_per_night": Decimal}``.
    Returns a JSON-ready dict; amounts are strings so no precision is lost.
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

"""Presentation filters for the Hotel MDJ templates."""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def cop(value):
    """Format an amount as Colombian pesos: 642600.00 -> "$642.600".

    COP is shown without cents and with dots as thousands separators, the
    way prices are written in Colombia. Values that are not numbers are
    returned unchanged so a template never breaks over a bad value.
    """
    try:
        amount = Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return value
    sign = "-" if amount < 0 else ""
    return f"{sign}${abs(amount):,}".replace(",", ".")

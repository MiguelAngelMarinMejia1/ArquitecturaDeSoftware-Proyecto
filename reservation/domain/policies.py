"""Pricing and tax rules for Hotel MDJ.

This module is where the UML operations ``Reserva.calcularTotal()`` and
``TipoHabitacion.calcularPrecioTemporada()`` actually live. Keeping them here
rather than on the models means a rate change never touches persistence code,
and every rule can be unit-tested without a database.

All money is handled with ``Decimal`` and rounded once, at the end, with
``ROUND_HALF_UP`` -- never with ``float``, which cannot represent currency
exactly.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings

CENTS = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    """Round a monetary amount to two decimal places."""
    return Decimal(value).quantize(CENTS, rounding=ROUND_HALF_UP)


class SeasonalPricingPolicy:
    """Resolves the nightly rate of a room type for a given date.

    UML origin: ``TipoHabitacion.calcularPrecioTemporada(fecha)``.

    The hotel has no seasonal calendar defined, so the base rate currently
    applies year-round. The date parameter is part of the signature anyway:
    high and low seasons are a rate concern, and this is the only class that
    should ever have to know about them.
    """

    def rate_for(self, room_type, on_date) -> Decimal:
        return _money(room_type.base_price_per_night)


@dataclass(frozen=True)
class PriceBreakdown:
    """Result of pricing a stay. Immutable: it is a value object, not state."""

    nights: int
    subtotal: Decimal
    taxes: Decimal
    total: Decimal
    price_per_night_by_room: dict

    def as_dict(self):
        return {
            "nights": self.nights,
            "subtotal": self.subtotal,
            "taxes": self.taxes,
            "total": self.total,
        }


class TaxPolicy:
    """Applies the tax rate configured for the hotel.

    The percentage is infrastructure configuration (``settings.TAX_RATE``), not
    a hard-coded domain constant, so it can differ per environment and be
    changed without touching this code.
    """

    def __init__(self, rate: Decimal | None = None):
        self._rate = Decimal(str(rate if rate is not None else settings.TAX_RATE))

    @property
    def rate(self) -> Decimal:
        return self._rate

    def taxes_for(self, subtotal: Decimal) -> Decimal:
        return _money(Decimal(subtotal) * self._rate)


class PricingPolicy:
    """Computes what a stay costs.

    UML origin: ``Reserva.calcularTotal()``.

    Collaborators are injected so the policy can be tested in isolation and so
    a different seasonal strategy can be swapped in without editing this class
    (Open/Closed).
    """

    def __init__(self, seasonal_policy=None, tax_policy=None):
        self._seasonal = seasonal_policy or SeasonalPricingPolicy()
        self._tax = tax_policy or TaxPolicy()

    @staticmethod
    def nights_between(check_in, check_out) -> int:
        """Number of billable nights. Assumes the range is already valid."""
        return (check_out - check_in).days

    def quote(self, rooms, check_in, check_out) -> PriceBreakdown:
        """Price a stay for a collection of rooms.

        Returns a :class:`PriceBreakdown` including the per-room nightly rate,
        which the service then freezes into each ``ReservationRoom`` row.
        """
        nights = self.nights_between(check_in, check_out)

        rate_by_room = {}
        subtotal = Decimal("0.00")
        for room in rooms:
            nightly = self._seasonal.rate_for(room.room_type, check_in)
            rate_by_room[room.pk] = nightly
            subtotal += nightly * nights

        subtotal = _money(subtotal)
        taxes = self._tax.taxes_for(subtotal)

        return PriceBreakdown(
            nights=nights,
            subtotal=subtotal,
            taxes=taxes,
            total=_money(subtotal + taxes),
            price_per_night_by_room=rate_by_room,
        )


class CapacityPolicy:
    """Answers whether a set of rooms can host a party of guests.

    Children count towards occupancy: a cot still occupies the room. Hotel MDJ
    can later introduce an age threshold by changing only this class.
    """

    @staticmethod
    def total_capacity(rooms) -> int:
        return sum(room.room_type.max_capacity for room in rooms)

    @classmethod
    def fits(cls, rooms, num_adults: int, num_children: int) -> bool:
        return (num_adults + num_children) <= cls.total_capacity(rooms)

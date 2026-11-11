"""Builder for the Reservation aggregate.

Why a Builder here? A reservation is the most complex entity in Hotel MDJ: it
ties together a customer, *one or more* rooms (UML multiplicity ``1..*``), a
date range, an occupancy split between adults and children, a frozen nightly
rate per room and three monetary totals. Assembling that with a single
constructor call would mean a long, order-dependent argument list where an
invalid combination is only discovered after the object exists.

The builder accumulates those parts through a fluent interface and runs every
invariant in ``build()``, so an invalid reservation can never be produced.

Responsibility boundary
-----------------------
``build()`` returns an **unsaved** aggregate. It does not touch the database,
does not send notifications and does not decide prices -- those belong to
``ReservationService`` and ``domain.policies`` respectively. This is what keeps
the class compliant with the Single Responsibility Principle: it builds and
validates, nothing else.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from reservation.domain.exceptions import (
    GuestCapacityExceededError,
    IncompleteReservationDataError,
    InvalidDateRangeError,
    NoRoomsSelectedError,
    RoomNotAvailableError,
)
from reservation.domain.policies import CapacityPolicy, PricingPolicy
from reservation.models import Reservation, ReservationRoom


@dataclass(frozen=True)
class ReservationDraft:
    """A fully validated, not yet persisted reservation aggregate.

    Holding the room lines alongside the reservation is what makes the ``1..*``
    association buildable in one atomic step: the service saves the parent and
    its lines inside a single transaction, or nothing at all.
    """

    reservation: Reservation
    room_lines: list = field(default_factory=list)
    breakdown: object = None


class ReservationBuilder:
    """Fluent builder that assembles and validates a reservation."""

    def __init__(self, pricing_policy=None, availability_checker=None):
        # Injected collaborators, so the builder can be unit-tested without a
        # database and so a different pricing strategy needs no edit here.
        self._pricing = pricing_policy or PricingPolicy()
        self._is_available = availability_checker or self._default_availability_checker

        self._customer = None
        self._rooms = []
        self._check_in = None
        self._check_out = None
        self._num_adults = None
        self._num_children = 0
        self._special_requests = ""
        self._confirmation_code = None

    # --- Fluent interface -------------------------------------------------

    def for_customer(self, customer):
        self._customer = customer
        return self

    def add_room(self, room):
        """Add one room. Called once per room to honour the ``1..*`` UML link."""
        if room is not None and room not in self._rooms:
            self._rooms.append(room)
        return self

    def add_rooms(self, rooms):
        for room in rooms or []:
            self.add_room(room)
        return self

    def with_dates(self, check_in: date, check_out: date):
        self._check_in = check_in
        self._check_out = check_out
        return self

    def with_guests(self, num_adults: int, num_children: int = 0):
        self._num_adults = num_adults
        self._num_children = num_children or 0
        return self

    def with_special_requests(self, special_requests: str):
        self._special_requests = (special_requests or "").strip()
        return self

    def with_confirmation_code(self, confirmation_code: str):
        self._confirmation_code = confirmation_code
        return self

    # --- Terminal operation ----------------------------------------------

    def build(self) -> ReservationDraft:
        """Validate every invariant and return an unsaved aggregate."""
        self._validate_completeness()
        self._validate_rooms_selected()
        self._validate_date_range()
        self._validate_guest_capacity()
        self._validate_room_availability()

        breakdown = self._pricing.quote(self._rooms, self._check_in, self._check_out)

        reservation = Reservation(
            customer=self._customer,
            check_in_date=self._check_in,
            check_out_date=self._check_out,
            num_adults=self._num_adults,
            num_children=self._num_children,
            special_requests=self._special_requests,
            confirmation_code=self._confirmation_code,
            subtotal=breakdown.subtotal,
            taxes=breakdown.taxes,
            total_amount=breakdown.total,
            status=Reservation.Status.PENDING,
        )

        room_lines = [
            ReservationRoom(
                room=room,
                price_per_night=breakdown.price_per_night_by_room.get(
                    room.pk, Decimal("0.00")
                ),
            )
            for room in self._rooms
        ]

        return ReservationDraft(
            reservation=reservation,
            room_lines=room_lines,
            breakdown=breakdown,
        )

    # --- Invariants -------------------------------------------------------

    def _validate_completeness(self):
        missing = [
            name
            for name, value in (
                (_("cliente"), self._customer),
                (_("fecha de entrada"), self._check_in),
                (_("fecha de salida"), self._check_out),
                (_("número de adultos"), self._num_adults),
                (_("código de confirmación"), self._confirmation_code),
            )
            if value is None
        ]
        if missing:
            raise IncompleteReservationDataError(
                _("Faltan datos requeridos para crear la reserva: %(fields)s.")
                % {"fields": ", ".join(missing)}
            )

    def _validate_rooms_selected(self):
        if not self._rooms:
            raise NoRoomsSelectedError(
                _("Una reserva debe incluir al menos una habitación.")
            )

    def _validate_date_range(self):
        if self._check_out <= self._check_in:
            raise InvalidDateRangeError(
                _("La fecha de salida debe ser posterior a la fecha de entrada.")
            )
        if self._check_in < date.today():
            raise InvalidDateRangeError(
                _("La fecha de entrada no puede estar en el pasado.")
            )

    def _validate_guest_capacity(self):
        if self._num_adults < 1:
            raise GuestCapacityExceededError(
                _("La reserva debe incluir al menos un adulto.")
            )
        if not CapacityPolicy.fits(self._rooms, self._num_adults, self._num_children):
            capacity = CapacityPolicy.total_capacity(self._rooms)
            guests = self._num_adults + self._num_children
            # Two plurals in one sentence: the capacity part and the requested
            # part are translated separately so each follows its own number.
            capacity_text = ngettext(
                "Las habitaciones seleccionadas admiten hasta %(capacity)d huésped",
                "Las habitaciones seleccionadas admiten hasta %(capacity)d huéspedes",
                capacity,
            ) % {"capacity": capacity}
            requested_text = ngettext(
                "se solicitó %(guests)d",
                "se solicitaron %(guests)d",
                guests,
            ) % {"guests": guests}
            raise GuestCapacityExceededError(
                _("%(capacity_text)s, pero %(requested_text)s.")
                % {"capacity_text": capacity_text, "requested_text": requested_text}
            )

    def _validate_room_availability(self):
        for room in self._rooms:
            if not self._is_available(room, self._check_in, self._check_out):
                raise RoomNotAvailableError(
                    _(
                        "La habitación %(number)s no está disponible entre "
                        "%(check_in)s y %(check_out)s."
                    )
                    % {
                        "number": room.number,
                        "check_in": self._check_in,
                        "check_out": self._check_out,
                    }
                )

    @staticmethod
    def _default_availability_checker(room, check_in, check_out):
        # Imported lazily to keep the module importable without Django apps
        # being ready (and to avoid a circular import with selectors).
        from reservation.selectors import is_room_available

        return is_room_available(room, check_in, check_out)

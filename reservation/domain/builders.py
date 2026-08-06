# reservation/domain/builders.py
"""Builder for the Reservation entity.

Responsibility: assemble a Reservation step by step (Fluent Interface) and
guarantee it is valid BEFORE it touches the database. This builder does NOT
calculate prices or handle state transitions (confirm/cancel) — those belong
to PricingCalculator and ReservationService respectively, to keep a single
responsibility here (SRP).
"""

from reservation.models import Reservation
from reservation.domain.exceptions import (
    IncompleteReservationDataError,
    InvalidDateRangeError,
    RoomNotAvailableError,
    GuestCapacityExceededError,
)


class ReservationBuilder:
    """Fluent builder that accumulates reservation data and validates it
    before persisting. Usage:

        reservation = (
            ReservationBuilder()
            .for_customer(customer)
            .for_room(room)
            .with_dates(check_in, check_out)
            .with_guests(4)
            .build()
        )
    """

    def __init__(self):
        # Internal state accumulated through the fluent chain.
        # Nothing is validated or saved until build() is called.
        self._customer = None
        self._room = None
        self._check_in_date = None
        self._check_out_date = None
        self._num_guests = None

    def for_customer(self, customer):
        """Sets the customer making the reservation. Returns self to allow chaining."""
        self._customer = customer
        return self

    def for_room(self, room):
        """Sets the room being reserved. Returns self to allow chaining."""
        self._room = room
        return self

    def with_dates(self, check_in_date, check_out_date):
        """Sets the requested date range. Returns self to allow chaining."""
        self._check_in_date = check_in_date
        self._check_out_date = check_out_date
        return self

    def with_guests(self, num_guests):
        """Sets the number of guests for the reservation. Returns self to allow chaining."""
        self._num_guests = num_guests
        return self

    def build(self) -> Reservation:
        """Validates all accumulated data and, if everything is correct,
        creates and persists the Reservation. Raises a specific domain
        exception on the first validation failure found — the Reservation
        is never partially saved."""

        self._validate_completeness()
        self._validate_date_range()
        self._validate_guest_capacity()
        self._validate_room_availability()

        # All checks passed: it's now safe to persist.
        reservation = Reservation.objects.create(
            customer=self._customer,
            room=self._room,
            check_in_date=self._check_in_date,
            check_out_date=self._check_out_date,
            num_guests=self._num_guests,
            status=Reservation.Status.PENDING,
        )
        return reservation

    # --- Internal validation steps -----------------------------------

    def _validate_completeness(self):
        """Ensures every required field was set before attempting to build."""
        missing = [
            name for name, value in [
                ("customer", self._customer),
                ("room", self._room),
                ("check_in_date", self._check_in_date),
                ("check_out_date", self._check_out_date),
                ("num_guests", self._num_guests),
            ] if value is None
        ]
        if missing:
            raise IncompleteReservationDataError(
                f"Missing required reservation data: {', '.join(missing)}"
            )

    def _validate_date_range(self):
        """Ensures check-in happens strictly before check-out."""
        if self._check_in_date >= self._check_out_date:
            raise InvalidDateRangeError(
                "check_in_date must be strictly before check_out_date."
            )

    def _validate_guest_capacity(self):
        """Ensures the number of guests fits the room type's max capacity."""
        max_capacity = self._room.room_type.max_capacity
        if self._num_guests > max_capacity:
            raise GuestCapacityExceededError(
                f"Room type '{self._room.room_type.name}' allows a maximum "
                f"of {max_capacity} guests, but {self._num_guests} were requested."
            )

    def _validate_room_availability(self):
        """Ensures the room has no other reservation overlapping the
        requested date range. Overlap rule: two ranges [a_in, a_out) and
        [b_in, b_out) overlap if a_in < b_out AND b_in < a_out."""
        overlapping = Reservation.objects.filter(
            room=self._room,
            status__in=[Reservation.Status.PENDING, Reservation.Status.CONFIRMED],
            check_in_date__lt=self._check_out_date,
            check_out_date__gt=self._check_in_date,
        ).exists()

        if overlapping:
            raise RoomNotAvailableError(
                f"Room {self._room.number} is not available between "
                f"{self._check_in_date} and {self._check_out_date}."
            )
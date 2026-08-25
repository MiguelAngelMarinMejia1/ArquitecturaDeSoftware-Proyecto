"""Read-side queries for the booking core.

Separating reads from the write services keeps ``services.py`` focused on
orchestrating changes. This module is also where the UML operation
``Habitacion.verificarDisponibilidad(entrada, salida)`` is implemented, kept
off the model so that no query logic hides in a persistence class.

Overlap rule
------------
Two stays collide when ``existing.check_in < new.check_out`` **and**
``existing.check_out > new.check_in``. The strict comparisons are deliberate:
a guest checking out on the 10th and another checking in on the 10th do not
overlap, because check-out happens before check-in on the same day.
"""

from django.db.models import Q

from reservation.models import Reservation, Room, RoomType

BLOCKING_STATUSES = (
    Reservation.Status.PENDING,
    Reservation.Status.CONFIRMED,
)


def _overlapping_reservation_rooms(check_in, check_out):
    """Room ids taken by a non-cancelled reservation in the given range."""
    return (
        Reservation.objects.filter(
            status__in=BLOCKING_STATUSES,
            check_in_date__lt=check_out,
            check_out_date__gt=check_in,
        )
        .values_list("reservation_rooms__room_id", flat=True)
        .distinct()
    )


def bookable_rooms():
    """Rooms the hotel is willing to sell at all."""
    return Room.objects.filter(
        is_active=True,
        status=Room.Status.AVAILABLE,
    ).select_related("room_type")


def available_rooms(check_in, check_out, guests=None, room_type=None):
    """Rooms free for the whole range, optionally filtered by party size/type.

    UML origin: ``Habitacion.verificarDisponibilidad()``.
    """
    queryset = bookable_rooms().exclude(
        pk__in=_overlapping_reservation_rooms(check_in, check_out)
    )

    if guests:
        queryset = queryset.filter(room_type__max_capacity__gte=guests)
    if room_type is not None:
        queryset = queryset.filter(room_type=room_type)

    return queryset.order_by("room_type__base_price_per_night", "number")


def is_room_available(room, check_in, check_out, exclude_reservation_id=None) -> bool:
    """Whether one specific room is free for the range.

    ``exclude_reservation_id`` lets a reservation be modified without colliding
    with itself.
    """
    if not room.is_active or room.status != Room.Status.AVAILABLE:
        return False

    clash = Reservation.objects.filter(
        Q(reservation_rooms__room=room),
        status__in=BLOCKING_STATUSES,
        check_in_date__lt=check_out,
        check_out_date__gt=check_in,
    )
    if exclude_reservation_id is not None:
        clash = clash.exclude(pk=exclude_reservation_id)

    return not clash.exists()


def room_types_catalog():
    """All room types, cheapest first -- used by the Home and search pages."""
    return RoomType.objects.all().order_by("base_price_per_night")


def find_reservation(confirmation_code: str, email: str):
    """Look a reservation up the way a guest without an account would.

    Requiring the e-mail as well as the code means a leaked or guessed code is
    not enough on its own to expose someone's personal data.
    """
    return (
        Reservation.objects.select_related("customer")
        .prefetch_related("reservation_rooms__room__room_type")
        .filter(
            confirmation_code__iexact=(confirmation_code or "").strip(),
            customer__email__iexact=(email or "").strip(),
        )
        .first()
    )

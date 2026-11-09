"""Background tasks run by the Celery worker (broker: Redis).

* ``send_reservation_confirmation``: delivers the confirmation of a booking
  outside the request, retrying with exponential backoff while the
  notification microservice is down.
* ``generate_occupancy_report``: builds an occupancy and revenue report for a
  date range, a query too heavy to run while a user waits for a page.
"""

import logging
from datetime import date, timedelta
from decimal import Decimal

from celery import shared_task
from django.db.models import Count, Sum

logger = logging.getLogger(__name__)


class NotificationNotDelivered(Exception):
    """Raised so Celery schedules another attempt."""


@shared_task(
    bind=True,
    autoretry_for=(NotificationNotDelivered,),
    retry_backoff=5,          # 5 s, 10 s, 20 s, 40 s ...
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=6,
)
def send_reservation_confirmation(self, reservation_id: int) -> dict:
    # Imported here so the worker loads the Django apps before the models.
    from reservation.infra.factories import NotifierFactory
    from reservation.models import Reservation

    reservation = (
        Reservation.objects.select_related("customer")
        .filter(pk=reservation_id)
        .first()
    )
    if reservation is None:
        # Nothing to retry: the booking no longer exists.
        logger.warning("Reservation %s not found, notification dropped", reservation_id)
        return {"reservation_id": reservation_id, "sent": False, "reason": "not_found"}

    from django.conf import settings

    notifier = NotifierFactory.create(settings.NOTIFIER_DELIVERY_TYPE)
    if not notifier.send_confirmation(reservation):
        logger.warning(
            "Notification for %s failed (attempt %s), retrying",
            reservation.confirmation_code,
            self.request.retries + 1,
        )
        raise NotificationNotDelivered(reservation.confirmation_code)

    return {
        "reservation_id": reservation_id,
        "confirmation_code": reservation.confirmation_code,
        "sent": True,
        "attempts": self.request.retries + 1,
    }


def _money(value) -> str:
    return str(Decimal(value or 0).quantize(Decimal("0.01")))


@shared_task
def generate_occupancy_report(date_from: str, date_to: str) -> dict:
    """Occupancy and revenue between two dates (``date_to`` exclusive).

    A night counts for the range when the guest sleeps there between
    ``date_from`` and ``date_to``, so stays that start before or end after
    the range only add the nights that fall inside it.
    """
    from reservation.models import Reservation, ReservationRoom, Room

    start = date.fromisoformat(date_from)
    end = date.fromisoformat(date_to)
    nights_in_range = (end - start).days

    overlapping = Reservation.objects.filter(
        check_in_date__lt=end, check_out_date__gt=start
    )
    by_status = {
        row["status"]: row["total"]
        for row in overlapping.values("status").annotate(total=Count("id"))
    }
    confirmed = overlapping.filter(status=Reservation.Status.CONFIRMED)

    room_nights_sold = 0
    for line in ReservationRoom.objects.filter(reservation__in=confirmed).select_related(
        "reservation"
    ):
        stay_start = max(line.reservation.check_in_date, start)
        stay_end = min(line.reservation.check_out_date, end)
        room_nights_sold += (stay_end - stay_start).days

    active_rooms = Room.objects.filter(is_active=True).count()
    capacity = active_rooms * nights_in_range
    occupancy = round(room_nights_sold * 100 / capacity, 2) if capacity else 0.0

    revenue = confirmed.aggregate(total=Sum("total_amount"))["total"]

    return {
        "date_from": start.isoformat(),
        "date_to": end.isoformat(),
        "nights": nights_in_range,
        "active_rooms": active_rooms,
        "reservations_by_status": by_status,
        "room_nights_sold": room_nights_sold,
        "room_nights_available": capacity,
        "occupancy_rate_percent": occupancy,
        # Whole booking amounts of confirmed stays touching the range.
        "confirmed_revenue": _money(revenue),
        "generated_on": date.today().isoformat(),
    }


def default_report_range():
    """Current calendar month: first day to first day of the next month."""
    today = date.today()
    start = today.replace(day=1)
    end = (start + timedelta(days=32)).replace(day=1)
    return start, end

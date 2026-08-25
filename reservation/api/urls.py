"""Routes for version 1 of the reservation API.

Mounted under ``/api/v1/`` by the project URLconf. Versioning the prefix from
the start means a future ``v2`` can run alongside this one while clients
migrate, and lets a gateway route by path without inspecting payloads.
"""

from django.urls import path

from reservation.api.views import (
    HealthView,
    ReservationCreateView,
    ReservationLookupView,
    RoomAvailabilityView,
    RoomTypeListView,
)

app_name = "reservation_api"

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("room-types/", RoomTypeListView.as_view(), name="room-type-list"),
    path("rooms/available/", RoomAvailabilityView.as_view(), name="room-availability"),
    path("reservations/", ReservationCreateView.as_view(), name="reservation-create"),
    path(
        "reservations/lookup/",
        ReservationLookupView.as_view(),
        name="reservation-lookup",
    ),
]

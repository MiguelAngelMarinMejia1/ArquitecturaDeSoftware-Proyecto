"""HTTP endpoints for the reservation core.

Plain ``APIView`` subclasses rather than ViewSets, so every method is explicit
about the status code it returns.

These views do three things and nothing more: validate the shape of the
request, delegate to a service, and serialise the result. There is no
business-level ``try/except`` here -- domain exceptions travel up to
``exception_handler.domain_exception_handler``, which owns the mapping to
400 / 404 / 409.
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from reservation.api.serializers import (
    AvailabilityQuerySerializer,
    ReservationCreateSerializer,
    ReservationLookupSerializer,
    ReservationReadSerializer,
    RoomSerializer,
    RoomTypeSerializer,
)
from reservation.selectors import available_rooms, room_types_catalog
from reservation.services import ReservationService


class RoomTypeListView(APIView):
    """Catalogue of room categories offered by the hotel."""

    def get(self, request):
        serializer = RoomTypeSerializer(room_types_catalog(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RoomAvailabilityView(APIView):
    """Rooms free for a date range.

    Search criteria travel in the query string because none of them identify a
    person, which also makes a result page shareable and cacheable.
    """

    def get(self, request):
        query = AvailabilityQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        criteria = query.validated_data

        rooms = available_rooms(
            check_in=criteria["check_in"],
            check_out=criteria["check_out"],
            guests=criteria["adults"] + criteria["children"],
            room_type=criteria.get("room_type"),
        )
        return Response(
            RoomSerializer(rooms, many=True).data, status=status.HTTP_200_OK
        )


class ReservationCreateView(APIView):
    """Creation of a reservation.

    Returns 201 on success. A malformed payload or a broken business rule
    yields 400, an unknown room 404, and a date clash 409.
    """

    def post(self, request):
        serializer = ReservationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reservation = ReservationService().create_reservation(serializer.validated_data)

        return Response(
            ReservationReadSerializer(reservation).data,
            status=status.HTTP_201_CREATED,
        )


class ReservationLookupView(APIView):
    """Retrieval of a reservation by confirmation code and e-mail.

    Modelled as POST rather than GET so the e-mail stays in the request body:
    a GET would leave it in browser history and access logs.
    """

    def post(self, request):
        serializer = ReservationLookupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reservation = ReservationService().lookup(
            confirmation_code=serializer.validated_data["confirmation_code"],
            email=serializer.validated_data["email"],
        )
        return Response(
            ReservationReadSerializer(reservation).data, status=status.HTTP_200_OK
        )


class HealthView(APIView):
    """Liveness probe consumed by the gateway or orchestrator."""

    def get(self, request):
        return Response({"status": "ok", "service": "reservation"})

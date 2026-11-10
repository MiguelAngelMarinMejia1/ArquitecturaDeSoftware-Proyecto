"""HTTP endpoints for the reservation core.

Plain ``APIView`` subclasses rather than ViewSets, so every method is explicit
about the status code it returns.

These views do three things and nothing more: validate the shape of the
request, delegate to a service, and serialise the result. There is no
business-level ``try/except`` here -- domain exceptions travel up to
``exception_handler.domain_exception_handler``, which owns the mapping to
400 / 404 / 409.
"""

import logging

from celery.result import AsyncResult
from django.urls import reverse
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from reservation.api.serializers import (
    AvailabilityQuerySerializer,
    ReportRequestSerializer,
    ReservationCreateSerializer,
    ReservationLookupSerializer,
    ReservationReadSerializer,
    RoomSerializer,
)
from reservation.selectors import available_rooms
from reservation.services import ReservationService
from reservation.tasks import default_report_range, generate_occupancy_report

logger = logging.getLogger(__name__)


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


class OccupancyReportView(APIView):
    """Starts an occupancy report in the background (Celery).

    Answers 202 at once with the task id; the worker builds the report and
    leaves it in Redis. Staff only: it exposes revenue.
    """

    permission_classes = [IsAdminUser]

    def post(self, request):
        query = ReportRequestSerializer(data=request.data)
        query.is_valid(raise_exception=True)
        default_from, default_to = default_report_range()
        date_from = query.validated_data.get("date_from") or default_from
        date_to = query.validated_data.get("date_to") or default_to

        try:
            task = generate_occupancy_report.delay(
                date_from.isoformat(), date_to.isoformat()
            )
        except Exception:  # broker (Redis) unreachable
            logger.exception("Could not queue the occupancy report")
            return Response(
                {
                    "error": {
                        "code": "SERVICEUNAVAILABLE",
                        "detail": "La cola de tareas no está disponible, intenta más tarde.",
                    }
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(
            {
                "task_id": task.id,
                "status": task.status,
                "result_url": request.build_absolute_uri(
                    reverse("reservation_api:report-result", args=[task.id])
                ),
            },
            status=status.HTTP_202_ACCEPTED,
        )


class ReportResultView(APIView):
    """State of a background report: PENDING, STARTED, SUCCESS or FAILURE."""

    permission_classes = [IsAdminUser]

    def get(self, request, task_id):
        result = AsyncResult(task_id, app=generate_occupancy_report.app)
        body = {"task_id": task_id, "status": result.status}
        if result.successful():
            body["report"] = result.result
        elif result.failed():
            body["error"] = "El reporte no se pudo generar."
        return Response(body, status=status.HTTP_200_OK)


class HealthView(APIView):
    """Liveness probe consumed by the gateway or orchestrator."""

    def get(self, request):
        return Response({"status": "ok", "service": "reservation"})

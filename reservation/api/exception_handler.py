"""Translation of domain errors into HTTP responses.

Registered as ``REST_FRAMEWORK['EXCEPTION_HANDLER']``, this runs for every
exception escaping an APIView. Centralising the mapping here is what lets the
views stay free of business-level ``try/except``: they call a service and let a
failure travel up as the domain exception it already is.

Every response shares one envelope, so a client -- or an API Gateway sitting in
front of this service -- can parse errors without special-casing each endpoint.
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from reservation.domain.exceptions import (
    GuestCapacityExceededError,
    IncompleteReservationDataError,
    InvalidDateRangeError,
    NoRoomsSelectedError,
    PaymentDeclinedError,
    ReservationDomainError,
    ReservationNotFoundError,
    RoomNotAvailableError,
    RoomNotFoundError,
)

DOMAIN_STATUS_MAP = {
    IncompleteReservationDataError: status.HTTP_400_BAD_REQUEST,
    InvalidDateRangeError: status.HTTP_400_BAD_REQUEST,
    GuestCapacityExceededError: status.HTTP_400_BAD_REQUEST,
    NoRoomsSelectedError: status.HTTP_400_BAD_REQUEST,
    PaymentDeclinedError: status.HTTP_402_PAYMENT_REQUIRED,
    RoomNotFoundError: status.HTTP_404_NOT_FOUND,
    ReservationNotFoundError: status.HTTP_404_NOT_FOUND,
    RoomNotAvailableError: status.HTTP_409_CONFLICT,
}


def _error_code(exc) -> str:
    """Stable machine-readable code derived from the exception class name."""
    return type(exc).__name__.removesuffix("Error").upper()


def domain_exception_handler(exc, context):
    if isinstance(exc, ReservationDomainError):
        # Unmapped subclasses fall back to 400 rather than surfacing as a 500:
        # a rule violation is the caller's problem, not a server fault.
        http_status = DOMAIN_STATUS_MAP.get(type(exc), status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "error": {
                    "code": _error_code(exc),
                    "detail": str(exc),
                }
            },
            status=http_status,
        )

    response = drf_exception_handler(exc, context)
    if response is not None:
        # Wrap DRF's own errors (validation, 404, throttling) in the same
        # envelope so clients only ever parse one shape.
        response.data = {
            "error": {
                "code": getattr(exc, "default_code", "ERROR").upper(),
                "detail": response.data,
            }
        }
    return response

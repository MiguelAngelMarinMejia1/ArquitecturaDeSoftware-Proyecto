"""Errors of the pricing service and how they become JSON responses.

Every error, whatever caused it, is answered with the same envelope the Django
API already uses, so a client parses one single shape:

    {
        "error": {
            "code": "INVALIDDATERANGE",
            "detail": "La fecha de salida debe ser posterior a la fecha de entrada."
        }
    }

How it works:
1. Our code raises one of the ``PricingError`` subclasses below.
2. Flask looks for a handler registered for that exception.
3. The handler turns it into the JSON above with the right status code.

To add a new error: create a subclass, set ``status_code`` and ``code``, and
raise it. No handler needs to change.
"""

import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


def error_response(code, detail, status_code):
    """Build the standard error envelope."""
    body = {"error": {"code": code, "detail": detail}}
    return jsonify(body), status_code


# --- Business errors (the caller sent something wrong -> 400) -------------


class PricingError(Exception):
    """Base class for every error this service raises on purpose."""

    status_code = 400
    code = "PRICINGERROR"

    def __init__(self, detail):
        super().__init__(detail)
        self.detail = detail


class InvalidPayloadError(PricingError):
    """The body is not JSON, or a field is missing or has the wrong type."""

    code = "INVALIDPAYLOAD"


class InvalidDateRangeError(PricingError):
    """Check-out is not after check-in, or check-in is in the past."""

    code = "INVALIDDATERANGE"


class NoRoomsSelectedError(PricingError):
    """The quote needs at least one room."""

    code = "NOROOMSSELECTED"


class InvalidPriceError(PricingError):
    """A nightly price is not a positive number."""

    code = "INVALIDPRICE"


# --- Registration ---------------------------------------------------------


def register_error_handlers(app):
    """Attach the JSON error handlers to the Flask app."""

    @app.errorhandler(PricingError)
    def handle_pricing_error(error):
        # Errors we raised ourselves: status and code come from the class.
        return error_response(error.code, error.detail, error.status_code)

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        # Errors Flask raises by itself: 404 (unknown URL), 405 (wrong method),
        # 415, etc. We keep Flask's status code and only change the format.
        code = error.name.upper().replace(" ", "")  # "Not Found" -> "NOTFOUND"
        return error_response(code, error.description, error.code)

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        # Anything else is a bug on our side. The details go to the logs, never
        # to the client, and the service keeps running for the next request.
        logger.exception("Unexpected error while handling the request")
        return error_response(
            "INTERNALSERVERERROR",
            "Ocurrio un error inesperado en el servicio de cotizacion.",
            500,
        )

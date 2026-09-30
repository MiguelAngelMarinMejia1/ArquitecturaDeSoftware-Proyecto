"""Errors of the pricing service and their JSON responses.

Every error uses the same envelope as the Django API:

    {"error": {"code": "INVALIDDATERANGE", "detail": "..."}}

To add an error: subclass ``PricingError``, set ``status_code`` and ``code``,
and raise it. The handlers below need no changes.
"""

import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


def error_response(code, detail, status_code):
    """Build the standard error envelope."""
    body = {"error": {"code": code, "detail": detail}}
    return jsonify(body), status_code


# --- Business errors (bad input -> 400) -----------------------------------


class PricingError(Exception):
    """Base class for every error this service raises on purpose."""

    status_code = 400
    code = "PRICINGERROR"

    def __init__(self, detail):
        super().__init__(detail)
        self.detail = detail


class InvalidPayloadError(PricingError):
    """Body is not JSON, or a field is missing or has the wrong type."""

    code = "INVALIDPAYLOAD"


class InvalidDateRangeError(PricingError):
    """Check-out not after check-in, or check-in in the past."""

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
        # Our own errors: status and code come from the class.
        return error_response(error.code, error.detail, error.status_code)

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        # Flask's own errors (404, 405, 415...): keep the status, change the format.
        code = error.name.upper().replace(" ", "")  # "Not Found" -> "NOTFOUND"
        return error_response(code, error.description, error.code)

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        # A bug on our side: log the details, send a generic message, keep serving.
        logger.exception("Unexpected error while handling the request")
        return error_response(
            "INTERNALSERVERERROR",
            "Ocurrio un error inesperado en el servicio de cotizacion.",
            500,
        )

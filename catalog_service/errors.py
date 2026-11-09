"""Errors of the catalog service and their JSON responses.

Same envelope as the Django API, so clients see no difference after the
gateway switched these routes to Flask:

    {"error": {"code": "INVALIDDATERANGE", "detail": "..."}}
"""

import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


def error_response(code, detail, status_code):
    body = {"error": {"code": code, "detail": detail}}
    return jsonify(body), status_code


class CatalogError(Exception):
    """Base class for every error this service raises on purpose."""

    status_code = 400
    code = "CATALOGERROR"

    def __init__(self, detail):
        super().__init__(detail)
        self.detail = detail


class InvalidQueryError(CatalogError):
    """A query string parameter is missing or malformed."""

    code = "INVALID"


class InvalidDateRangeError(CatalogError):
    """Check-out not after check-in. Code kept as Django's serializer sends it."""

    code = "INVALID"


class DataSourceUnavailableError(CatalogError):
    """The database is unreachable or not migrated yet."""

    status_code = 503
    code = "SERVICEUNAVAILABLE"


def register_error_handlers(app):
    @app.errorhandler(CatalogError)
    def handle_catalog_error(error):
        return error_response(error.code, error.detail, error.status_code)

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        code = error.name.upper().replace(" ", "")
        return error_response(code, error.description, error.code)

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        logger.exception("Unexpected error while handling the request")
        return error_response(
            "INTERNALSERVERERROR",
            "Ocurrió un error inesperado en el servicio de catálogo.",
            500,
        )

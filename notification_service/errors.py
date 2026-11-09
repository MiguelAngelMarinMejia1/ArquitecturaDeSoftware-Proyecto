"""Errors of the notification service, answered with the shared JSON envelope."""

import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


def error_response(code, detail, status_code):
    return jsonify({"error": {"code": code, "detail": detail}}), status_code


class NotificationError(Exception):
    status_code = 400
    code = "NOTIFICATIONERROR"

    def __init__(self, detail):
        super().__init__(detail)
        self.detail = detail


class InvalidPayloadError(NotificationError):
    code = "INVALIDPAYLOAD"


class NotificationNotFoundError(NotificationError):
    status_code = 404
    code = "NOTIFICATIONNOTFOUND"


def register_error_handlers(app):
    @app.errorhandler(NotificationError)
    def handle_notification_error(error):
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
            "Ocurrió un error inesperado en el servicio de notificaciones.",
            500,
        )

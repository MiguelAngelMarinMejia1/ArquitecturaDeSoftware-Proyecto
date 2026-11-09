"""Notification microservice (Flask).

Strangled from the Django monolith: the confirmation e-mail used to be sent
in-process (``ConsoleNotifier`` / ``EmailNotifier``). Now Django posts a
``RESERVATION_CONFIRMED`` event here through the Nginx gateway with its
``HttpNotifier`` adapter.

    GET  /api/v2/notificaciones/health/
    POST /api/v2/notificaciones/          send -> 201 (SENT) / 502 (FAILED)
    GET  /api/v2/notificaciones/<code>/   notifications of a reservation
                                          (recipient e-mail masked)
"""

from flask import Flask, jsonify, request

from auth import internal_only
from channels import build_channel, render_confirmation
from config import Config
from errors import NotificationNotFoundError, register_error_handlers
from repository import NotificationRepository
from validation import parse_notification_request

URL_PREFIX = "/api/v2/notificaciones"


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.json.sort_keys = app.config["JSON_SORT_KEYS"]
    register_error_handlers(app)

    channel = build_channel(app.config)
    repository = NotificationRepository(app.config["DATABASE_URL"])

    @app.get(f"{URL_PREFIX}/health/", strict_slashes=False)
    def health():
        return jsonify({"status": "ok", "service": "notifications"}), 200

    @app.post(f"{URL_PREFIX}/", strict_slashes=False)
    @internal_only
    def notify():
        data = parse_notification_request(request.get_json(silent=True))
        subject, body = render_confirmation(data)
        sent, error = channel.send(data["recipient_email"], subject, body)
        record = repository.save(
            event=data["event"],
            confirmation_code=data["confirmation_code"],
            recipient_email=data["recipient_email"],
            channel=channel.NAME,
            sent=sent,
            error=error,
        )
        return jsonify(record), (201 if sent else 502)

    @app.get(f"{URL_PREFIX}/<code>/", strict_slashes=False)
    def by_reservation(code):
        records = repository.by_confirmation_code(code)
        if not records:
            raise NotificationNotFoundError(
                f"No hay notificaciones para la reserva '{code}'."
            )
        return jsonify(records), 200

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=app.config["PORT"], debug=False)

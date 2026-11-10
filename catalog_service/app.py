"""Catalog microservice (Flask): rooms and room availability.

Strangled from the Django monolith. Nginx now sends these legacy URLs here
instead of to Django, keeping the exact same JSON contract:

    GET /api/v1/rooms/?page=1&page_size=12
    GET /api/v1/rooms/available/?check_in=...&check_out=...&adults=&children=&room_type=

Plus its own probe:

    GET /api/v2/catalogo/health/
"""

import os

from flask import Flask, jsonify, request

from config import Config
from errors import InvalidQueryError, register_error_handlers
from repository import CatalogRepository
from validation import parse_availability_query, parse_pagination_query


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.json.sort_keys = app.config["JSON_SORT_KEYS"]
    register_error_handlers(app)

    repository = CatalogRepository(
        app.config["DATABASE_URL"],
        os.environ.get("MEDIA_BASE_URL", "http://localhost/media/"),
    )

    @app.get("/api/v2/catalogo/health/", strict_slashes=False)
    def health():
        return jsonify({"status": "ok", "service": "catalog"}), 200

    @app.get("/api/v1/rooms/", strict_slashes=False)
    def rooms():
        page, page_size = parse_pagination_query(request.args)
        return jsonify(repository.rooms_page(page, page_size)), 200

    @app.get("/api/v1/rooms/available/", strict_slashes=False)
    def available_rooms():
        criteria = parse_availability_query(request.args)

        room_type_id = criteria["room_type_id"]
        if room_type_id is not None and not repository.room_type_exists(room_type_id):
            raise InvalidQueryError(
                {"room_type": [f'Clave primaria "{room_type_id}" inválida - objeto no existe.']}
            )

        rooms = repository.available_rooms(
            check_in=criteria["check_in"],
            check_out=criteria["check_out"],
            guests=criteria["guests"],
            room_type_id=room_type_id,
        )
        return jsonify(rooms), 200

    return app


# Object gunicorn loads in Docker: ``gunicorn app:app``.
app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=app.config["PORT"], debug=False)

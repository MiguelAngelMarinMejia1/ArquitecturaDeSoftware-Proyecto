"""Entry point of the Hotel MDJ pricing microservice (Flask).

This service is the first piece "strangled" out of the Django monolith: it
owns the rules that turn nightly rates and a date range into a price quote.
It does not use a database -- everything it needs arrives in the request JSON.

Run it locally:

    pip install -r requirements.txt
    python app.py

Nginx sends every request under ``/api/v2/cotizacion/`` to this service, so
all routes below keep that prefix.
"""

from flask import Flask, jsonify

from config import Config
from errors import register_error_handlers

# Every route of this service lives under this prefix. Change it here and in
# nginx/nginx.conf if the public URL ever changes.
URL_PREFIX = "/api/v2/cotizacion"


def create_app(config_class=Config):
    """Build and configure the Flask application.

    Using a function (an "application factory") instead of a global object
    lets tests or other environments pass a different configuration.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.json.sort_keys = app.config["JSON_SORT_KEYS"]

    # Every error (400, 404, 405, 500...) is answered as structured JSON.
    register_error_handlers(app)

    @app.get(f"{URL_PREFIX}/health/", strict_slashes=False)
    def health():
        """Liveness probe: answers 200 while the service is up."""
        return jsonify({"status": "ok", "service": "pricing"}), 200

    return app


# gunicorn (inside Docker) imports this object: ``gunicorn app:app``.
app = create_app()


if __name__ == "__main__":
    # Development server. host="0.0.0.0" makes it reachable from outside the
    # machine or container; debug stays off so errors use our JSON handlers.
    app.run(host="0.0.0.0", port=app.config["PORT"], debug=False)

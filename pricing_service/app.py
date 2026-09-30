"""Hotel MDJ pricing microservice (Flask).

First feature strangled out of the Django monolith: turns nightly rates and a
date range into a price quote. No database; everything arrives in the JSON.

Run locally:

    pip install -r requirements.txt
    python app.py

Nginx forwards ``/api/v2/cotizacion/...`` here, so every route keeps that prefix.
"""

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from flask import Flask, jsonify, request

from config import Config
from errors import register_error_handlers
from pricing import build_quote
from validation import parse_quote_request

# Public prefix of every route. If it changes, update nginx/nginx.conf too.
URL_PREFIX = "/api/v2/cotizacion"


def create_app(config_class=Config):
    """Build the Flask app. Pass another config class for tests or other envs."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.json.sort_keys = app.config["JSON_SORT_KEYS"]

    # Every error (400, 404, 405, 500...) is answered as structured JSON.
    register_error_handlers(app)

    @app.get(f"{URL_PREFIX}/health/", strict_slashes=False)
    def health():
        """Liveness probe."""
        return jsonify({"status": "ok", "service": "pricing"}), 200

    @app.post(f"{URL_PREFIX}/", strict_slashes=False)
    def create_quote():
        """POST /api/v2/cotizacion/ -- read, validate, price.

        Any error raised along the way is turned into JSON by errors.py.
        """
        # silent=True gives None for a non-JSON body; validation answers 400.
        payload = request.get_json(silent=True)

        today = datetime.now(ZoneInfo(app.config["TIME_ZONE"])).date()
        data = parse_quote_request(payload, today)

        quote = build_quote(
            rooms=data["rooms"],
            check_in=data["check_in"],
            check_out=data["check_out"],
            tax_rate=Decimal(app.config["TAX_RATE"]),
        )
        return jsonify(quote), 200

    return app


# Object gunicorn loads in Docker: ``gunicorn app:app``.
app = create_app()


if __name__ == "__main__":
    # Dev server. 0.0.0.0 = reachable from outside; debug off so errors use
    # our JSON handlers.
    app.run(host="0.0.0.0", port=app.config["PORT"], debug=False)

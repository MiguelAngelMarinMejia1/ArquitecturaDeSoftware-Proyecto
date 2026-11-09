"""Payment microservice (Flask).

Strangled from the Django monolith: charging a reservation used to happen
in-process (``SimulatedGateway``). Now Django calls this service through the
Nginx gateway with its ``HttpPaymentGateway`` adapter.

    GET  /api/v2/pagos/health/
    POST /api/v2/pagos/                 charge -> 201 (approved) / 402 (declined)
    GET  /api/v2/pagos/<reference>/     look a transaction up
"""

from flask import Flask, jsonify, request

from config import Config
from errors import PaymentNotFoundError, register_error_handlers
from providers import build_provider
from repository import PaymentRepository
from validation import parse_charge_request

URL_PREFIX = "/api/v2/pagos"


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.json.sort_keys = app.config["JSON_SORT_KEYS"]
    register_error_handlers(app)

    provider = build_provider(app.config["PROVIDER"])
    repository = PaymentRepository(app.config["SQLITE_PATH"])

    @app.get(f"{URL_PREFIX}/health/", strict_slashes=False)
    def health():
        return jsonify({"status": "ok", "service": "payments"}), 200

    @app.post(f"{URL_PREFIX}/", strict_slashes=False)
    def charge():
        data = parse_charge_request(request.get_json(silent=True))
        approved, reference, message = provider.charge(
            data["amount"], data["method"], data["reference_hint"]
        )
        transaction = repository.save(
            reference=reference,
            reference_hint=data["reference_hint"],
            amount=data["amount"],
            method=data["method"],
            provider=provider.NAME,
            approved=approved,
            message=message,
        )
        return jsonify(transaction), (201 if approved else 402)

    @app.get(f"{URL_PREFIX}/<reference>/", strict_slashes=False)
    def detail(reference):
        transaction = repository.get(reference)
        if transaction is None:
            raise PaymentNotFoundError(f"No existe el pago con referencia '{reference}'.")
        return jsonify(transaction), 200

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=app.config["PORT"], debug=False)

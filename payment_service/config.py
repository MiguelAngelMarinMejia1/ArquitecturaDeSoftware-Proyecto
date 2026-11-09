"""Configuration of the payment microservice (environment variables)."""

import os


class Config:
    # Own PostgreSQL database: payment transactions are no longer the
    # monolith's data.
    DATABASE_URL = os.environ.get(
        "DATABASE_URL", "postgresql://payments:payments@localhost:5432/payments"
    )

    # Name of the provider this service simulates. A real one (Wompi, PayU,
    # Stripe) would replace SimulatedProvider in providers.py.
    PROVIDER = os.environ.get("PAYMENT_PROVIDER", "SIMULATED")

    # Shared secret callers must send in X-Internal-Token (see auth.py).
    INTERNAL_API_TOKEN = os.environ.get("INTERNAL_API_TOKEN", "")

    PORT = int(os.environ.get("PORT", "5002"))
    JSON_SORT_KEYS = False

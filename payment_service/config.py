"""Configuration of the payment microservice (environment variables)."""

import os
from pathlib import Path

_DEFAULT_DB = Path(__file__).resolve().parent / "payments.sqlite3"


class Config:
    # Own database: payment transactions are no longer the monolith's data.
    SQLITE_PATH = os.environ.get("SQLITE_PATH", str(_DEFAULT_DB))

    # Name of the provider this service simulates. A real one (Wompi, PayU,
    # Stripe) would replace SimulatedProvider in providers.py.
    PROVIDER = os.environ.get("PAYMENT_PROVIDER", "SIMULATED")

    PORT = int(os.environ.get("PORT", "5002"))
    JSON_SORT_KEYS = False

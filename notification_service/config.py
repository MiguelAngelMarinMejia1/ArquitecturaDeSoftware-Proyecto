"""Configuration of the notification microservice (environment variables)."""

import os


class Config:
    # Own PostgreSQL database: log of every notification sent.
    DATABASE_URL = os.environ.get(
        "DATABASE_URL",
        "postgresql://notifications:notifications@localhost:5432/notifications",
    )

    # Delivery channel: CONSOLE (prints, for development) | EMAIL (SMTP).
    CHANNEL = os.environ.get("NOTIFICATION_CHANNEL", "CONSOLE")

    # Only used by the EMAIL channel.
    SMTP_HOST = os.environ.get("SMTP_HOST", "localhost")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "25"))
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "false").lower() == "true"
    MAIL_FROM = os.environ.get("MAIL_FROM", "reservas@hotelmdj.com")

    # Shared secret callers must send in X-Internal-Token (see auth.py).
    INTERNAL_API_TOKEN = os.environ.get("INTERNAL_API_TOKEN", "")

    PORT = int(os.environ.get("PORT", "5003"))
    JSON_SORT_KEYS = False

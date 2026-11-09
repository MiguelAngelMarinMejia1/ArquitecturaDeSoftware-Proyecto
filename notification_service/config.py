"""Configuration of the notification microservice (environment variables)."""

import os
from pathlib import Path

_DEFAULT_DB = Path(__file__).resolve().parent / "notifications.sqlite3"


class Config:
    # Own database: log of every notification sent.
    SQLITE_PATH = os.environ.get("SQLITE_PATH", str(_DEFAULT_DB))

    # Delivery channel: CONSOLE (prints, for development) | EMAIL (SMTP).
    CHANNEL = os.environ.get("NOTIFICATION_CHANNEL", "CONSOLE")

    # Only used by the EMAIL channel.
    SMTP_HOST = os.environ.get("SMTP_HOST", "localhost")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "25"))
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "false").lower() == "true"
    MAIL_FROM = os.environ.get("MAIL_FROM", "reservas@hotelmdj.com")

    PORT = int(os.environ.get("PORT", "5003"))
    JSON_SORT_KEYS = False

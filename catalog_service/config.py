"""Configuration of the catalog microservice.

Every value comes from an environment variable with a local default, so the
same code runs with ``python app.py`` and inside Docker.
"""

import os
from pathlib import Path

# Without Docker, read the monolith's SQLite file at the project root.
_DEFAULT_DB = Path(__file__).resolve().parent.parent / "db.sqlite3"


class Config:
    # SQLite file written by the Django monolith. This service only reads it
    # (opened in read-only mode). Shared database = transitional step of the
    # Strangler Pattern until the catalog gets its own store.
    SQLITE_PATH = os.environ.get("SQLITE_PATH", str(_DEFAULT_DB))

    # Only used by ``python app.py``; in Docker, gunicorn sets the port.
    PORT = int(os.environ.get("PORT", "5001"))

    # Keep JSON keys in the order we write them.
    JSON_SORT_KEYS = False

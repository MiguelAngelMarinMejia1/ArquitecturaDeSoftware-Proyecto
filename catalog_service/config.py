"""Configuration of the catalog microservice.

Every value comes from an environment variable with a local default, so the
same code runs with ``python app.py`` and inside Docker.
"""

import os


class Config:
    # The monolith's PostgreSQL database, reached with the read-only role
    # catalog_reader (see postgres/init/01-databases.sh). Sharing it is the
    # transitional step of the Strangler Pattern until the catalog gets its
    # own store.
    DATABASE_URL = os.environ.get(
        "DATABASE_URL",
        "postgresql://catalog_reader:catalog_reader@localhost:5432/hotelmdj",
    )

    # Only used by ``python app.py``; in Docker, gunicorn sets the port.
    PORT = int(os.environ.get("PORT", "5001"))

    # Keep JSON keys in the order we write them.
    JSON_SORT_KEYS = False

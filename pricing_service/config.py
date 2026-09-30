"""Configuration of the pricing microservice.

Every value comes from an environment variable with a local default, so the
same code runs with ``python app.py`` and inside Docker. Change a value by
setting the variable, not by editing this file.
"""

import os


class Config:
    # Tax on top of the room subtotal (0.19 = 19 %). A string, so it becomes
    # an exact Decimal later.
    TAX_RATE = os.environ.get("TAX_RATE", "0.19")

    # Decides what "today" is when rejecting past dates. Matches Django's TIME_ZONE.
    TIME_ZONE = os.environ.get("TIME_ZONE", "America/Bogota")

    # Only used by ``python app.py``; in Docker, gunicorn sets the port.
    PORT = int(os.environ.get("PORT", "5000"))

    # Keep JSON keys in the order we write them.
    JSON_SORT_KEYS = False

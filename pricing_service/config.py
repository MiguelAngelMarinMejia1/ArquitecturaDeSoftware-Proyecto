"""Configuration for the pricing microservice.

Every value is read from an environment variable with a sensible default, so
the same code runs on a laptop (``python app.py``) and inside Docker, where
``docker-compose.yml`` sets the variables.

To change a value you never edit this file: you set the variable instead.
"""

import os


class Config:
    # Tax applied on top of the room subtotal (0.19 = 19 %).
    # Kept as a string so it can be turned into an exact Decimal later.
    TAX_RATE = os.environ.get("TAX_RATE", "0.19")

    # Time zone used to decide what "today" means when rejecting past dates.
    # It matches TIME_ZONE in the Django settings.
    TIME_ZONE = os.environ.get("TIME_ZONE", "America/Bogota")

    # Port used only when the service is started with ``python app.py``.
    # Inside Docker, gunicorn decides the port (see the Dockerfile).
    PORT = int(os.environ.get("PORT", "5000"))

    # Keep the key order we write in the JSON responses instead of sorting it.
    JSON_SORT_KEYS = False

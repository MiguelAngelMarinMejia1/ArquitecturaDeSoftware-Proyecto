"""Service-to-service authentication.

The POST endpoint is published through the Nginx gateway, so anyone reaching
the gateway could call it. Callers must therefore send the shared secret in
``X-Internal-Token``. If ``INTERNAL_API_TOKEN`` is empty (local runs) the
check is skipped.
"""

import hmac
from functools import wraps

from flask import current_app, request

from errors import error_response

HEADER = "X-Internal-Token"


def internal_only(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        expected = current_app.config["INTERNAL_API_TOKEN"]
        received = request.headers.get(HEADER, "")
        if expected and not hmac.compare_digest(received, expected):
            return error_response(
                "FORBIDDEN", "Este endpoint solo acepta llamadas internas.", 403
            )
        return view(*args, **kwargs)

    return wrapper

"""Storage of payment transactions in the service's own PostgreSQL database.

The ``payments`` database and role belong to this service alone (see
postgres/init/01-databases.sh); the monolith cannot reach them.
"""

from datetime import datetime, timezone

import psycopg

_SCHEMA = """
CREATE TABLE IF NOT EXISTS payment_transaction (
    id              BIGSERIAL      PRIMARY KEY,
    reference       VARCHAR(40)    NOT NULL UNIQUE,
    reference_hint  VARCHAR(40)    NOT NULL DEFAULT '',
    amount          NUMERIC(12, 2) NOT NULL CHECK (amount > 0),
    method          VARCHAR(20)    NOT NULL,
    provider        VARCHAR(20)    NOT NULL,
    status          VARCHAR(10)    NOT NULL,
    message         TEXT           NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ    NOT NULL
)
"""

_COLUMNS = "reference, reference_hint, amount, method, provider, status, message, created_at"
_KEYS = [c.strip() for c in _COLUMNS.split(",")]


def _as_dict(row):
    data = dict(zip(_KEYS, row))
    data["amount"] = str(data["amount"])
    data["created_at"] = data["created_at"].isoformat(timespec="seconds")
    data["approved"] = data["status"] == "APPROVED"
    return data


class PaymentRepository:
    def __init__(self, database_url):
        self._url = database_url
        with self._connect() as conn:
            # Several gunicorn workers start at once: the advisory lock makes
            # them create the table one after the other.
            conn.execute("SELECT pg_advisory_xact_lock(hashtext('payment_schema'))")
            conn.execute(_SCHEMA)

    def _connect(self):
        return psycopg.connect(self._url, connect_timeout=5)

    def save(self, *, reference, reference_hint, amount, method, provider, approved, message):
        row = (
            reference,
            reference_hint,
            amount,
            method,
            provider,
            "APPROVED" if approved else "DECLINED",
            message,
            datetime.now(timezone.utc).replace(microsecond=0),
        )
        with self._connect() as conn:
            conn.execute(
                f"INSERT INTO payment_transaction ({_COLUMNS}) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                row,
            )
        return _as_dict(row)

    def get(self, reference):
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT {_COLUMNS} FROM payment_transaction WHERE reference = %s",
                (reference,),
            ).fetchone()
        return _as_dict(row) if row else None

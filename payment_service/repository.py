"""Storage of payment transactions in the service's own SQLite database."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS payment_transaction (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    reference       TEXT    NOT NULL UNIQUE,
    reference_hint  TEXT    NOT NULL DEFAULT '',
    amount          TEXT    NOT NULL,
    method          TEXT    NOT NULL,
    provider        TEXT    NOT NULL,
    status          TEXT    NOT NULL,
    message         TEXT    NOT NULL DEFAULT '',
    created_at      TEXT    NOT NULL
)
"""

_COLUMNS = "reference, reference_hint, amount, method, provider, status, message, created_at"


def _as_dict(row):
    keys = [c.strip() for c in _COLUMNS.split(",")]
    data = dict(zip(keys, row))
    data["approved"] = data["status"] == "APPROVED"
    return data


class PaymentRepository:
    def __init__(self, sqlite_path):
        self._path = sqlite_path
        Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(_SCHEMA)

    def _connect(self):
        return sqlite3.connect(self._path, timeout=5)

    def save(self, *, reference, reference_hint, amount, method, provider, approved, message):
        row = (
            reference,
            reference_hint,
            str(amount),
            method,
            provider,
            "APPROVED" if approved else "DECLINED",
            message,
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
        with self._connect() as conn:
            conn.execute(
                f"INSERT INTO payment_transaction ({_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                row,
            )
        return _as_dict(row)

    def get(self, reference):
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT {_COLUMNS} FROM payment_transaction WHERE reference = ?",
                (reference,),
            ).fetchone()
        return _as_dict(row) if row else None

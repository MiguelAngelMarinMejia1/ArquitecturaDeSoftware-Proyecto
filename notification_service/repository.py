"""Log of notifications in the service's own SQLite database."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS notification (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    event              TEXT NOT NULL,
    confirmation_code  TEXT NOT NULL,
    recipient_email    TEXT NOT NULL,
    channel            TEXT NOT NULL,
    status             TEXT NOT NULL,
    error              TEXT NOT NULL DEFAULT '',
    created_at         TEXT NOT NULL
)
"""

_INDEX = "CREATE INDEX IF NOT EXISTS ix_notification_code ON notification (confirmation_code)"


def mask_email(email):
    """ana.perez@mail.com -> a********@mail.com (never publish full addresses)."""
    local, _, domain = email.partition("@")
    return f"{local[:1]}{'*' * max(len(local) - 1, 1)}@{domain}"


def _public(row):
    return {
        "id": row[0],
        "event": row[1],
        "confirmation_code": row[2],
        "recipient": mask_email(row[3]),
        "channel": row[4],
        "status": row[5],
        "created_at": row[6],
    }


class NotificationRepository:
    def __init__(self, sqlite_path):
        self._path = sqlite_path
        Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(_SCHEMA)
            conn.execute(_INDEX)

    def _connect(self):
        return sqlite3.connect(self._path, timeout=5)

    def save(self, *, event, confirmation_code, recipient_email, channel, sent, error):
        created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        status = "SENT" if sent else "FAILED"
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO notification (event, confirmation_code, recipient_email, "
                "channel, status, error, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (event, confirmation_code, recipient_email, channel, status, error, created_at),
            )
            row_id = cursor.lastrowid
        return _public(
            (row_id, event, confirmation_code, recipient_email, channel, status, created_at)
        )

    def by_confirmation_code(self, confirmation_code):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, event, confirmation_code, recipient_email, channel, status, "
                "created_at FROM notification WHERE confirmation_code = ? ORDER BY id",
                (confirmation_code,),
            ).fetchall()
        return [_public(row) for row in rows]

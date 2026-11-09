"""Log of notifications in the service's own PostgreSQL database.

The ``notifications`` database and role belong to this service alone (see
postgres/init/01-databases.sh).
"""

from datetime import datetime, timezone

import psycopg

_SCHEMA = """
CREATE TABLE IF NOT EXISTS notification (
    id                 BIGSERIAL    PRIMARY KEY,
    event              VARCHAR(40)  NOT NULL,
    confirmation_code  VARCHAR(20)  NOT NULL,
    recipient_email    VARCHAR(254) NOT NULL,
    channel            VARCHAR(20)  NOT NULL,
    status             VARCHAR(10)  NOT NULL,
    error              TEXT         NOT NULL DEFAULT '',
    created_at         TIMESTAMPTZ  NOT NULL
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
        "created_at": row[6].isoformat(timespec="seconds"),
    }


class NotificationRepository:
    def __init__(self, database_url):
        self._url = database_url
        with self._connect() as conn:
            # Serialises schema creation across gunicorn workers.
            conn.execute("SELECT pg_advisory_xact_lock(hashtext('notification_schema'))")
            conn.execute(_SCHEMA)
            conn.execute(_INDEX)

    def _connect(self):
        return psycopg.connect(self._url, connect_timeout=5)

    def save(self, *, event, confirmation_code, recipient_email, channel, sent, error):
        created_at = datetime.now(timezone.utc).replace(microsecond=0)
        status = "SENT" if sent else "FAILED"
        with self._connect() as conn:
            row_id = conn.execute(
                "INSERT INTO notification (event, confirmation_code, recipient_email, "
                "channel, status, error, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
                (event, confirmation_code, recipient_email, channel, status, error, created_at),
            ).fetchone()[0]
        return _public(
            (row_id, event, confirmation_code, recipient_email, channel, status, created_at)
        )

    def by_confirmation_code(self, confirmation_code):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, event, confirmation_code, recipient_email, channel, status, "
                "created_at FROM notification WHERE confirmation_code = %s ORDER BY id",
                (confirmation_code,),
            ).fetchall()
        return [_public(row) for row in rows]

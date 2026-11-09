"""Read-only access to the room catalog stored by the monolith (PostgreSQL).

Ports ``reservation/selectors.py`` to plain SQL. Connects as
``catalog_reader``, a role that can only SELECT, inside read-only
transactions: this service can never change the monolith's data.

Overlap rule, unchanged: two stays collide when
``existing.check_in < new.check_out`` and ``existing.check_out > new.check_in``
(strict, so a same-day check-out and check-in do not collide).
"""

import logging
from decimal import ROUND_HALF_UP, Decimal

import psycopg

from errors import DataSourceUnavailableError

logger = logging.getLogger(__name__)

# Statuses that keep a room occupied. Cancelled reservations free it.
BLOCKING_STATUSES = ["PENDING", "CONFIRMED"]

_ROOM_TYPE_COLUMNS = (
    "rt.id, rt.name, rt.description, rt.max_capacity, rt.bed_type, "
    "rt.base_price_per_night"
)


def _money(value):
    """Publishes amounts as "180000.00", like Django's DecimalField."""
    return str(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _room_type_dict(row, offset=0):
    return {
        "id": row[offset],
        "name": row[offset + 1],
        "description": row[offset + 2],
        "max_capacity": row[offset + 3],
        "bed_type": row[offset + 4],
        "base_price_per_night": _money(row[offset + 5]),
    }


class CatalogRepository:
    def __init__(self, database_url):
        self._url = database_url

    def _query(self, sql, params=()):
        try:
            with psycopg.connect(self._url, connect_timeout=3) as conn:
                conn.read_only = True
                return conn.execute(sql, params).fetchall()
        except psycopg.errors.UndefinedTable as exc:
            # Django has not run its migrations yet.
            raise DataSourceUnavailableError(
                "El catálogo aún no está listo, intenta de nuevo en unos segundos."
            ) from exc
        except psycopg.OperationalError as exc:
            logger.error("Catalog database unreachable: %s", exc)
            raise DataSourceUnavailableError(
                "La base de datos del catálogo no está disponible."
            ) from exc

    def room_types(self):
        rows = self._query(
            f"SELECT {_ROOM_TYPE_COLUMNS} FROM reservation_roomtype rt "
            "ORDER BY rt.base_price_per_night, rt.id"
        )
        return [_room_type_dict(row) for row in rows]

    def room_type_exists(self, room_type_id):
        rows = self._query(
            "SELECT 1 FROM reservation_roomtype WHERE id = %s", (room_type_id,)
        )
        return bool(rows)

    def available_rooms(self, check_in, check_out, guests=None, room_type_id=None):
        sql = (
            "SELECT r.id, r.number, r.floor, r.status, "
            f"{_ROOM_TYPE_COLUMNS} "
            "FROM reservation_room r "
            "JOIN reservation_roomtype rt ON rt.id = r.room_type_id "
            "WHERE r.is_active AND r.status = 'AVAILABLE' "
            "AND r.id NOT IN ("
            "  SELECT rr.room_id FROM reservation_reservationroom rr "
            "  JOIN reservation_reservation res ON res.id = rr.reservation_id "
            "  WHERE res.status = ANY(%s) "
            "  AND res.check_in_date < %s AND res.check_out_date > %s"
            ")"
        )
        params = [BLOCKING_STATUSES, check_out, check_in]

        if guests:
            sql += " AND rt.max_capacity >= %s"
            params.append(guests)
        if room_type_id is not None:
            sql += " AND rt.id = %s"
            params.append(room_type_id)

        sql += " ORDER BY rt.base_price_per_night, r.number"

        return [
            {
                "id": row[0],
                "number": row[1],
                "floor": row[2],
                "status": row[3],
                "room_type": _room_type_dict(row, offset=4),
            }
            for row in self._query(sql, params)
        ]

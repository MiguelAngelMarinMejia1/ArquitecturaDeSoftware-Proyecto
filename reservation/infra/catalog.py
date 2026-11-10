"""HTTP adapter for the catalog microservice.

The web layer consumes catalog data through this adapter instead of knowing
the catalog service URL or its JSON representation. Reservation writes still
use Django's database transaction and ORM.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings


class CatalogServiceError(Exception):
    """The catalog service could not provide a valid response."""


@dataclass(frozen=True)
class CatalogRoomType:
    id: int
    name: str
    description: str
    max_capacity: int
    bed_type: str
    base_price_per_night: Decimal

    @property
    def pk(self):
        return self.id


@dataclass(frozen=True)
class CatalogRoom:
    id: int
    number: str
    floor: int
    status: str
    image_urls: list[str]
    room_type: CatalogRoomType

    @property
    def pk(self):
        return self.id


class CatalogClient:
    """Adapter translating catalog HTTP responses into application objects."""

    def __init__(self, base_url=None, timeout=None, session=None):
        configured_url = base_url or settings.CATALOG_SERVICE_URL
        self._base_url = configured_url.rstrip("/") + "/"
        self._timeout = timeout or settings.MICROSERVICE_TIMEOUT
        self._session = session or requests

    def rooms(self, page=1, page_size=12):
        payload = self._get(
            "rooms/",
            params={"page": page, "page_size": page_size},
        )
        if not isinstance(payload, dict) or not isinstance(payload.get("rooms"), list):
            raise CatalogServiceError("El catálogo devolvió un formato inválido.")
        return {
            "page": self._required_int(payload, "page"),
            "page_size": self._required_int(payload, "page_size"),
            "total": self._required_int(payload, "total"),
            "total_pages": self._required_int(payload, "total_pages"),
            "rooms": [self._parse_room(item) for item in payload["rooms"]],
        }

    def available_rooms(self, check_in, check_out, adults, children):
        payload = self._get(
            "rooms/available/",
            params={
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "adults": adults,
                "children": children,
            },
        )
        if not isinstance(payload, list):
            raise CatalogServiceError("El catálogo devolvió un formato inválido.")
        return [self._parse_room(item) for item in payload]

    def _get(self, path, params=None):
        try:
            response = self._session.get(
                self._base_url + path,
                params=params,
                timeout=self._timeout,
            )
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            raise CatalogServiceError(
                "El catálogo no está disponible en este momento."
            ) from exc

    @classmethod
    def _parse_room_type(cls, payload):
        if not isinstance(payload, dict):
            raise CatalogServiceError("El catálogo devolvió una habitación inválida.")
        return CatalogRoomType(
            id=cls._required_int(payload, "id"),
            name=cls._required_text(payload, "name"),
            description=cls._required_text(payload, "description", allow_empty=True),
            max_capacity=cls._required_int(payload, "max_capacity"),
            bed_type=cls._required_text(payload, "bed_type", allow_empty=True),
            base_price_per_night=cls._required_decimal(
                payload, "base_price_per_night"
            ),
        )

    @classmethod
    def _parse_room(cls, payload):
        if not isinstance(payload, dict):
            raise CatalogServiceError("El catálogo devolvió una habitación inválida.")
        return CatalogRoom(
            id=cls._required_int(payload, "id"),
            number=cls._required_text(payload, "number"),
            floor=cls._required_int(payload, "floor"),
            status=cls._required_text(payload, "status"),
            image_urls=cls._optional_urls(payload, "image_urls"),
            room_type=cls._parse_room_type(payload.get("room_type")),
        )

    @staticmethod
    def _required_text(payload, name, allow_empty=False):
        value = payload.get(name)
        if not isinstance(value, str) or (not allow_empty and not value.strip()):
            raise CatalogServiceError(f"El catálogo no contiene '{name}' válido.")
        return value

    @staticmethod
    def _optional_urls(payload, name):
        value = payload.get(name, [])
        if value in (None, ""):
            return []
        if not isinstance(value, list):
            raise CatalogServiceError(f"El catálogo no contiene '{name}' válido.")
        return [
            CatalogClient._optional_url({"url": item}, "url")
            for item in value
        ]

    @staticmethod
    def _required_int(payload, name):
        value = payload.get(name)
        if isinstance(value, bool) or not isinstance(value, int):
            raise CatalogServiceError(f"El catálogo no contiene '{name}' válido.")
        return value

    @staticmethod
    def _required_decimal(payload, name):
        value = payload.get(name)
        try:
            decimal_value = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise CatalogServiceError(
                f"El catálogo no contiene '{name}' válido."
            ) from exc
        if not decimal_value.is_finite():
            raise CatalogServiceError(f"El catálogo no contiene '{name}' válido.")
        return decimal_value

    @staticmethod
    def _optional_url(payload, name):
        value = payload.get(name)
        if value in (None, ""):
            return None
        if not isinstance(value, str) or len(value) > 500:
            raise CatalogServiceError(f"El catálogo no contiene '{name}' válido.")
        return value

"""Adapter for the public API-Colombia tourism catalog."""

from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.utils.translation import gettext as _


class TourismServiceError(Exception):
    """The public tourism API could not provide valid attractions."""


def _invalid_field(name):
    return _("API-Colombia no contiene '%(field)s' válido.") % {"field": name}


@dataclass(frozen=True)
class TouristAttraction:
    id: int
    name: str
    description: str
    city: str
    department: str
    image_url: str


class TourismClient:
    """Translate API-Colombia data into a stable internal read model."""

    def __init__(self, base_url=None, timeout=None, session=None):
        configured_url = base_url or settings.API_COLOMBIA_URL
        self._url = configured_url.rstrip("/") + "/"
        self._timeout = timeout or settings.MICROSERVICE_TIMEOUT
        self._session = session or requests

    def list_attractions(self, limit=6):
        try:
            response = self._session.get(self._url, timeout=self._timeout)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise TourismServiceError(
                _("Los lugares turísticos no están disponibles en este momento.")
            ) from exc

        if not isinstance(payload, list):
            raise TourismServiceError(_("API-Colombia devolvió un formato inválido."))
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        return [self._parse_attraction(item) for item in payload[:limit]]

    @classmethod
    def _parse_attraction(cls, payload):
        if not isinstance(payload, dict):
            raise TourismServiceError(_("API-Colombia devolvió un lugar inválido."))
        return TouristAttraction(
            id=cls._required_int(payload, "id"),
            name=cls._required_text(payload, "name"),
            description=cls._optional_text(payload, "description"),
            city=cls._nested_name(payload.get("city")),
            department=cls._nested_name(payload.get("department")),
            image_url=cls._image_url(payload.get("images")),
        )

    @staticmethod
    def _required_int(payload, name):
        value = payload.get(name)
        if isinstance(value, bool) or not isinstance(value, int):
            raise TourismServiceError(_invalid_field(name))
        return value

    @staticmethod
    def _required_text(payload, name):
        value = payload.get(name)
        if not isinstance(value, str) or not value.strip():
            raise TourismServiceError(_invalid_field(name))
        return value

    @staticmethod
    def _optional_text(payload, name):
        value = payload.get(name, "")
        if value is None:
            return ""
        if isinstance(value, list):
            value = value[0] if value else ""
        if not isinstance(value, str):
            return ""
        return value

    @staticmethod
    def _nested_name(value):
        if isinstance(value, dict):
            return TourismClient._optional_text(value, "name")
        return TourismClient._optional_text({"value": value}, "value")

    @staticmethod
    def _image_url(value):
        if isinstance(value, list):
            value = next((item for item in value if isinstance(item, str)), "")
        if not isinstance(value, str):
            return ""
        parsed = urlparse(value.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return ""
        return value.strip()

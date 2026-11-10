"""Adapter for the allied MeetU2 experiences API."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings


class ExperiencesServiceError(Exception):
    """MeetU2 did not provide a valid experiences response."""


@dataclass(frozen=True)
class Experience:
    id: str
    title: str
    description: str
    category: str
    city: str
    location: str
    starts_at: datetime
    price: Decimal
    available_slots: int
    organizer: str


class ExperiencesClient:
    """Translate MeetU2's external contract into application DTOs."""

    def __init__(self, base_url=None, timeout=None, session=None):
        configured_url = base_url or settings.MEETU2_API_URL
        self._url = configured_url.rstrip("/") + "/"
        self._timeout = timeout or settings.MICROSERVICE_TIMEOUT
        self._session = session or requests

    def list_public_experiences(self):
        try:
            response = self._session.get(self._url, timeout=self._timeout)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise ExperiencesServiceError(
                "Las experiencias aliadas no están disponibles en este momento."
            ) from exc

        if not isinstance(payload, dict) or not isinstance(
            payload.get("experiencias"), list
        ):
            raise ExperiencesServiceError("MeetU2 devolvió un formato inválido.")

        return [self._parse_experience(item) for item in payload["experiencias"]]

    @classmethod
    def _parse_experience(cls, payload):
        if not isinstance(payload, dict):
            raise ExperiencesServiceError("MeetU2 devolvió una experiencia inválida.")
        try:
            starts_at = datetime.fromisoformat(cls._text(payload, "fecha_hora"))
        except ValueError as exc:
            raise ExperiencesServiceError(
                "MeetU2 devolvió una fecha inválida."
            ) from exc
        return Experience(
            id=cls._text(payload, "id"),
            title=cls._text(payload, "titulo"),
            description=cls._text(payload, "descripcion"),
            category=cls._text(payload, "categoria"),
            city=cls._text(payload, "ciudad"),
            location=cls._text(payload, "ubicacion"),
            starts_at=starts_at,
            price=cls._decimal(payload, "precio"),
            available_slots=cls._int(payload, "cupo_disponible"),
            organizer=cls._text(payload, "organizador"),
        )

    @staticmethod
    def _text(payload, name):
        value = payload.get(name)
        if not isinstance(value, str) or not value.strip():
            raise ExperiencesServiceError(f"MeetU2 no contiene '{name}' válido.")
        return value

    @staticmethod
    def _int(payload, name):
        value = payload.get(name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ExperiencesServiceError(f"MeetU2 no contiene '{name}' válido.")
        return value

    @staticmethod
    def _decimal(payload, name):
        try:
            value = Decimal(str(payload.get(name)))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ExperiencesServiceError(f"MeetU2 no contiene '{name}' válido.") from exc
        if not value.is_finite() or value < 0:
            raise ExperiencesServiceError(f"MeetU2 no contiene '{name}' válido.")
        return value

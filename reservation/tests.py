from datetime import date
from unittest.mock import Mock

from django.test import SimpleTestCase

from reservation.infra.catalog import CatalogClient, CatalogServiceError
from reservation.infra.experiences import (
    ExperiencesClient,
    ExperiencesServiceError,
)
from reservation.infra.tourism import TourismClient, TourismServiceError


class CatalogClientTests(SimpleTestCase):
    def _client(self, payload):
        response = Mock()
        response.json.return_value = payload
        response.raise_for_status.return_value = None
        session = Mock()
        session.get.return_value = response
        return CatalogClient(
            base_url="http://catalog.test/api/v1/",
            session=session,
        ), session

    def test_available_rooms_send_search_criteria(self):
        client, session = self._client(
            [
                {
                    "id": 1,
                    "number": "101",
                    "floor": 1,
                    "status": "AVAILABLE",
                    "image_urls": [
                        "https://cdn.example.com/rooms/101-1.jpg",
                        "https://cdn.example.com/rooms/101-2.jpg",
                    ],
                    "room_type": {
                        "id": 1,
                        "name": "Sencilla",
                        "description": "Para una persona.",
                        "max_capacity": 1,
                        "bed_type": "Cama sencilla",
                        "base_price_per_night": "180000.00",
                    },
                }
            ]
        )

        rooms = client.available_rooms(date(2026, 12, 10), date(2026, 12, 13), 1, 0)

        self.assertEqual(rooms[0].pk, 1)
        self.assertEqual(rooms[0].room_type.name, "Sencilla")
        self.assertEqual(len(rooms[0].image_urls), 2)
        session.get.assert_called_once_with(
            "http://catalog.test/api/v1/rooms/available/",
            params={
                "check_in": "2026-12-10",
                "check_out": "2026-12-13",
                "adults": 1,
                "children": 0,
            },
            timeout=5.0,
        )

    def test_rooms_parse_paginated_catalog(self):
        client, session = self._client(
            {
                "page": 1,
                "page_size": 12,
                "total": 9,
                "total_pages": 1,
                "rooms": [
                    {
                        "id": 1,
                        "number": "101",
                        "floor": 1,
                        "status": "AVAILABLE",
                        "image_urls": [],
                        "room_type": {
                            "id": 1,
                            "name": "Sencilla",
                            "description": "",
                            "max_capacity": 1,
                            "bed_type": "Cama sencilla",
                            "base_price_per_night": "180000.00",
                        },
                    }
                ],
            }
        )

        page = client.rooms()

        self.assertEqual(page["page"], 1)
        self.assertEqual(page["total"], 9)
        self.assertEqual(page["rooms"][0].number, "101")
        session.get.assert_called_once_with(
            "http://catalog.test/api/v1/rooms/",
            params={"page": 1, "page_size": 12},
            timeout=5.0,
        )

    def test_invalid_payload_is_rejected(self):
        client, _ = self._client({"unexpected": "shape"})

        with self.assertRaises(CatalogServiceError):
            client.rooms()


class ExperiencesClientTests(SimpleTestCase):
    def _client(self, payload):
        response = Mock()
        response.json.return_value = payload
        response.raise_for_status.return_value = None
        session = Mock()
        session.get.return_value = response
        return ExperiencesClient(
            base_url="http://meet2u.test/api/v1/integracion/experiencias-publicas/",
            session=session,
        ), session

    def test_parse_public_experiences_without_calling_external_api(self):
        client, session = self._client(
            {
                "plataforma": "MeetU2",
                "version": "2.0",
                "descripcion": "Experiencias públicas",
                "total": 1,
                "experiencias": [
                    {
                        "id": "experience-1",
                        "titulo": "Taller de barismo",
                        "descripcion": "Aprende espresso.",
                        "categoria": "Gastronomia",
                        "ciudad": "Medellin",
                        "ubicacion": "Casa Rose",
                        "fecha_hora": "2026-10-26T04:03:54.160579+00:00",
                        "precio": 40000.0,
                        "cupo_disponible": 7,
                        "organizador": "Host ID c5298021",
                    }
                ],
            }
        )

        experiences = client.list_public_experiences()

        self.assertEqual(experiences[0].title, "Taller de barismo")
        self.assertEqual(str(experiences[0].price), "40000.0")
        self.assertEqual(experiences[0].available_slots, 7)
        session.get.assert_called_once_with(
            "http://meet2u.test/api/v1/integracion/experiencias-publicas/",
            timeout=5.0,
        )

    def test_invalid_experience_payload_is_rejected(self):
        client, _ = self._client({"experiencias": [{"titulo": "Incompleta"}]})

        with self.assertRaises(ExperiencesServiceError):
            client.list_public_experiences()


class TourismClientTests(SimpleTestCase):
    def test_parse_tourist_attractions_without_external_request(self):
        response = Mock()
        response.json.return_value = [
            {
                "id": 1,
                "name": "Museo de Antioquia",
                "description": "Museo de arte en Medellín.",
                "city": "Medellín",
                "department": "Antioquia",
                "images": ["https://example.com/museo.jpg"],
            }
        ]
        response.raise_for_status.return_value = None
        session = Mock()
        session.get.return_value = response
        client = TourismClient(
            base_url="https://api-colombia.test/api/v1/TouristicAttraction",
            session=session,
        )

        attractions = client.list_attractions()

        self.assertEqual(attractions[0].name, "Museo de Antioquia")
        self.assertEqual(attractions[0].image_url, "https://example.com/museo.jpg")
        self.assertEqual(attractions[0].city, "Medellín")
        session.get.assert_called_once_with(
            "https://api-colombia.test/api/v1/TouristicAttraction/",
            timeout=5.0,
        )

    def test_limit_keeps_the_public_page_compact(self):
        response = Mock()
        response.json.return_value = [
            {"id": number, "name": f"Lugar {number}"} for number in range(10)
        ]
        response.raise_for_status.return_value = None
        session = Mock()
        session.get.return_value = response
        client = TourismClient(
            base_url="https://api-colombia.test/api/v1/TouristicAttraction",
            session=session,
        )

        attractions = client.list_attractions(limit=3)

        self.assertEqual(len(attractions), 3)

    def test_invalid_tourism_payload_is_rejected(self):
        response = Mock()
        response.json.return_value = {"data": []}
        response.raise_for_status.return_value = None
        session = Mock()
        session.get.return_value = response
        client = TourismClient(
            base_url="https://api-colombia.test/api/v1/TouristicAttraction",
            session=session,
        )

        with self.assertRaises(TourismServiceError):
            client.list_attractions()

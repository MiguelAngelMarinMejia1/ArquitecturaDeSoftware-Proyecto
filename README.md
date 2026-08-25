# Hotel MDJ

Sistema de reservas para el **Hotel MDJ**, desarrollado con **Python, Django y Django Rest
Framework** como proyecto de la asignatura **Arquitectura de Software 2026**.

## Descripción

El sistema permite consultar disponibilidad y crear reservas de habitaciones sin necesidad de tener
una cuenta, siguiendo el modelo de los sistemas de gestión hotelera reales. La lógica de negocio
está desacoplada de la presentación mediante una **Service Layer**, y el núcleo se expone a través
de dos capas independientes: un sitio web renderizado en servidor y una API REST versionada.

## Arquitectura

Las dependencias apuntan siempre hacia el núcleo: `web` conoce a `reservation`, pero `reservation`
no conoce a `web`, y solo su subpaquete `api/` sabe que existe HTTP.

| Capa | Ubicación | Responsabilidad |
|---|---|---|
| Presentación HTML | `web/` | Vistas delgadas y plantillas |
| Presentación API | `reservation/api/` | Serializers, `APIView`, mapeo a códigos HTTP |
| Aplicación | `reservation/services.py`, `selectors.py` | Orquestación de casos de uso y consultas |
| Dominio | `reservation/domain/` | Builder, políticas de precio y capacidad, excepciones |
| Infraestructura | `reservation/infra/` | Factories, notificaciones, pasarela de pago |
| Persistencia | `reservation/models.py` | Entidades sin lógica de negocio |

## Patrones de diseño

- **Builder** — `ReservationBuilder` ensambla y valida la reserva, la entidad más compleja del
  sistema, y devuelve un agregado sin persistir para que el servicio controle la transacción.
- **Factory** — `NotifierFactory` y `PaymentGatewayFactory` resuelven qué implementación de
  notificador y de pasarela construir según la configuración del entorno.

## Tecnologías

- Python 3.11
- Django 5.2
- Django Rest Framework 3.18
- SQLite
- HTML semántico

## Puesta en marcha

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

python manage.py migrate
python manage.py loaddata seed
python manage.py runserver
```

| URL | Descripción |
|---|---|
| `/` | Página de inicio |
| `/reservaciones/` | Flujo de reserva |
| `/reservaciones/consultar/` | Consulta de una reserva existente |
| `/api/v1/` | API REST |
| `/admin/` | Administración |

## API

| Método | Ruta | Códigos |
|---|---|---|
| `GET` | `/api/v1/health/` | 200 |
| `GET` | `/api/v1/room-types/` | 200 |
| `GET` | `/api/v1/rooms/available/` | 200, 400 |
| `POST` | `/api/v1/reservations/` | 201, 400, 402, 404, 409 |
| `POST` | `/api/v1/reservations/lookup/` | 200, 400, 404 |

Todos los errores comparten un mismo contrato:

```json
{
  "error": {
    "code": "ROOMNOTAVAILABLE",
    "detail": "La habitacion 103 no esta disponible entre 2026-09-03 y 2026-09-06."
  }
}
```

## Diagrama de clases

<img width="831" height="1600" alt="Diagrama de clases de Hotel MDJ" src="https://github.com/user-attachments/assets/ac772ebb-6a25-4bf4-8fb8-18028dfd9107" />

## Documentación técnica

La documentación detallada está en la **Wiki** del repositorio:

1. Arquitectura y estructura de carpetas
2. Diagrama de secuencia de Crear Reserva
3. Estrategia de API Gateway y escalabilidad
4. Patrones creacionales
5. Identidad y autenticación
6. Seguridad de los datos personales

## Equipo

Proyecto desarrollado para la Entrega 1 de Arquitectura de Software 2026.

## Licencia

Proyecto con fines académicos.

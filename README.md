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

### Migración a microservicios (Strangler Pattern)

La cotización de precios (noches, tarifa por habitación, impuestos y total) se extrajo del
monolito a un microservicio independiente en **Flask** (`pricing_service/`). No usa base de
datos: recibe todo en el JSON. **Nginx** es la única puerta de entrada y reparte el tráfico por URL:

| Ruta | Destino |
|---|---|
| `/api/v2/cotizacion/` | Microservicio Flask (`pricing_service`) |
| `/api/v1/` | Monolito Django |
| `/` (web, admin, estáticos) | Monolito Django |

## Patrones de diseño

- **Builder** — `ReservationBuilder` ensambla y valida la reserva, la entidad más compleja del
  sistema, y devuelve un agregado sin persistir para que el servicio controle la transacción.
- **Factory** — `NotifierFactory` y `PaymentGatewayFactory` resuelven qué implementación de
  notificador y de pasarela construir según la configuración del entorno.

## Tecnologías

- Python 3.11
- Django 5.2
- Django Rest Framework 3.18
- Flask 3.1 + gunicorn (microservicio de cotización)
- SQLite
- Nginx 1.30
- Docker y Docker Compose
- HTML semántico

## Puesta en marcha con Docker

Levanta Django, Flask y Nginx juntos. Requiere Docker Desktop.

```bash
docker compose up --build
```

Abre `http://localhost`. Las migraciones y los datos de ejemplo (`seed`) se cargan solos al
arrancar el contenedor de Django, y la base SQLite se guarda en el volumen `sqlite_data`.

| Comando | Para qué |
|---|---|
| `docker compose up -d --build` | Levantar en segundo plano |
| `docker compose logs -f` | Ver los logs de los tres servicios |
| `docker compose restart nginx` | Recargar tras editar `nginx/nginx.conf` |
| `docker compose down` | Detener y borrar contenedores |
| `docker compose down -v` | Además, borrar la base de datos |

Si el puerto 80 está ocupado, cambia `"80:80"` por `"8080:80"` en `docker-compose.yml`.

## Puesta en marcha sin Docker

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

python manage.py migrate
python manage.py loaddata seed
python manage.py runserver
```

Microservicio de cotización (en otra terminal), disponible en `http://localhost:5000/api/v2/cotizacion/`:

```bash
cd pricing_service
pip install -r requirements.txt
python app.py
```

| URL | Descripción |
|---|---|
| `/` | Página de inicio |
| `/reservaciones/` | Flujo de reserva |
| `/reservaciones/consultar/` | Consulta de una reserva existente |
| `/api/v1/` | API REST |
| `/admin/` | Administración |

## API

### API v1 (monolito Django)

| Método | Ruta | Códigos |
|---|---|---|
| `GET` | `/api/v1/health/` | 200 |
| `GET` | `/api/v1/room-types/` | 200 |
| `GET` | `/api/v1/rooms/available/` | 200, 400 |
| `POST` | `/api/v1/reservations/` | 201, 400, 402, 404, 409 |
| `POST` | `/api/v1/reservations/lookup/` | 200, 400, 404 |

### API v2 (microservicio Flask)

| Método | Ruta | Códigos |
|---|---|---|
| `GET` | `/api/v2/cotizacion/health/` | 200 |
| `POST` | `/api/v2/cotizacion/` | 200, 400, 405, 500 |

```json
POST /api/v2/cotizacion/
{
  "check_in_date": "2026-10-10",
  "check_out_date": "2026-10-13",
  "rooms": [
    { "room_id": 1, "price_per_night": "180000.00" },
    { "room_id": 5, "price_per_night": "250000.00" }
  ]
}
```

```json
{
  "check_in_date": "2026-10-10",
  "check_out_date": "2026-10-13",
  "nights": 3,
  "rooms": [
    { "room_id": 1, "price_per_night": "180000.00", "nights": 3, "line_total": "540000.00" },
    { "room_id": 5, "price_per_night": "250000.00", "nights": 3, "line_total": "750000.00" }
  ],
  "subtotal": "1290000.00",
  "tax_rate": "0.19",
  "taxes": "245100.00",
  "total": "1535100.00"
}
```

Todos los errores, de ambas versiones de la API, comparten un mismo contrato:

```json
{
  "error": {
    "code": "ROOMNOTAVAILABLE",
    "detail": "La habitacion 103 no esta disponible entre 2026-09-03 y 2026-09-06."
  }
}
```

## Diagrama de clases

<img width="1872" height="3437" alt="mermaid-diagram-1787716945265" src="https://github.com/user-attachments/assets/8d097eb8-c338-4b5f-91ba-d8951c972c3f" />

## Documentación técnica

La documentación detallada está en la **Wiki** del repositorio:

1. Arquitectura y estructura de carpetas
2. Diagrama de secuencia de Crear Reserva
3. Estrategia de API Gateway y escalabilidad
4. Patrones creacionales
5. Identidad y autenticación
6. Seguridad de los datos personales
7. Migración a Microservicios (Strangler Pattern)

## Equipo

Proyecto desarrollado para la Entrega 1 de Arquitectura de Software 2026.

## Licencia

Proyecto con fines académicos.

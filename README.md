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

Each `Room` stores its image URLs in `image_urls`, separated by commas in the
admin, and the room catalog API returns them as a JSON list. This lets each
physical room have its own gallery while `RoomType` keeps shared catalogue
data such as capacity and price. In production, use S3/CloudFront for those
URLs. The web templates use the first image and keep the existing CSS artwork
as a fallback when the list is empty.

The public room catalog is `GET /api/v1/rooms/?page=1&page_size=12`. It does
not calculate date availability and returns at most 12 rooms per page:

```json
{"page": 1, "page_size": 12, "total": 9, "total_pages": 1, "rooms": []}
```

The booking flow uses `GET /api/v1/rooms/available/` with dates and guest
counts, because only that endpoint performs availability filtering.

### Integración con MeetU2

El menú **Experiencias** abre `/experiencias/`, una página independiente del
flujo de reservas. Django consume la API aliada de MeetU2 mediante
`reservation/infra/experiences.py` y transforma su contrato externo en objetos
de lectura antes de entregarlos a la plantilla. La URL se configura con
`MEETU2_API_URL` y por defecto es:

`http://184.193.170.74/api/v1/integracion/experiencias-publicas/`

La integración no modifica habitaciones, disponibilidad ni reservas. Si AWS
Academy está apagada o MeetU2 devuelve un error, la página muestra un mensaje
no bloqueante en lugar de afectar el resto del sitio. Esta API aliada es
independiente de cualquier futura API de terceros.

La API de terceros seleccionada es **API-Colombia**, una API pública sin
autenticación que ofrece atracciones turísticas del país. Se consume mediante
el adapter independiente `reservation/infra/tourism.py` y se presenta en
`/lugares/`, sin compartir modelos ni lógica con MeetU2. Su URL se configura
con `API_COLOMBIA_URL`; el valor predeterminado es
`https://api-colombia.com/api/v1/TouristicAttraction`.

### Migración a microservicios (Strangler Pattern)

Cuatro funcionalidades se extrajeron del monolito a microservicios **Flask** independientes,
cada uno con su propio Dockerfile. **Nginx** es la única puerta de entrada (API Gateway) y
reparte el tráfico por URL:

| Microservicio | Carpeta | Datos | Qué reemplaza en Django |
|---|---|---|---|
| Cotización | `pricing_service/` | Sin BD | `PricingPolicy` |
| Catálogo y disponibilidad | `catalog_service/` | Lee la base `hotelmdj` del monolito con un rol de **solo lectura** | `RoomAvailabilityView` |
| Pagos | `payment_service/` | Base propia `payments` | `SimulatedGateway` |
| Notificaciones | `notification_service/` | Base propia `notifications` | `ConsoleNotifier` / `EmailNotifier` |

| Ruta | Destino |
|---|---|
| `/api/v1/rooms/`, `/api/v1/rooms/available/` | Flask `catalog_service` (catálogo público y disponibilidad) |
| `/api/v2/catalogo/` | Flask `catalog_service` |
| `/api/v2/cotizacion/` | Flask `pricing_service` |
| `/api/v2/pagos/` | Flask `payment_service` |
| `/api/v2/notificaciones/` | Flask `notification_service` |
| Resto de `/api/v1/` | Monolito Django (crear y consultar reservas) |
| `/` (web, admin, estáticos) | Monolito Django |

Django consume pagos y notificaciones **a través de Nginx** mediante dos adapters
(`HttpPaymentGateway` y `HttpNotifier`), registrados en las factories existentes con el
tipo `HTTP`. La web también consume el catálogo y la disponibilidad mediante
`reservation/infra/catalog.py` (`CatalogClient`), que llama a `/api/v1/rooms/` para el
catálogo y a `/api/v1/rooms/available/` con un timeout configurable. La creación de reservas conserva
la validación final y las escrituras en la base de Django para mantener su transacción.

- Si el servicio de pagos no responde, el cobro se trata como rechazado (402) y la
  transacción de la reserva se revierte: nunca queda una reserva confirmada sin pago.
- Si el servicio de notificaciones no responde, la reserva se confirma igual y el fallo
  queda en el log.
- Los `POST` de pagos y notificaciones exigen la cabecera `X-Internal-Token` con el secreto
  `INTERNAL_API_TOKEN`, porque Nginx los expone públicamente.
- Que el catálogo comparta la base del monolito es un paso transitorio del patrón: el
  siguiente es darle su propio almacén.

### Base de datos (PostgreSQL)

Un contenedor `postgres` con una base y un rol por dueño de los datos, creados por
`postgres/init/01-databases.sh` la primera vez que arranca:

| Base | Rol | Quién la usa |
|---|---|---|
| `hotelmdj` | `hotelmdj` | Django y el worker de Celery |
| `hotelmdj` | `catalog_reader` (solo `SELECT`, transacciones de solo lectura) | `catalog_service` |
| `payments` | `payments` | `payment_service` |
| `notifications` | `notifications` | `notification_service` |

Ningún servicio puede conectarse a la base de otro. Sin Docker, Django sigue usando
`db.sqlite3` mientras no se defina `POSTGRES_HOST`.

### Comunicación asíncrona (Redis + Celery)

**Redis** es el message broker y **Celery** el worker de tareas en segundo plano
(contenedores `redis` y `celery_worker`).

- **Notificaciones.** Al confirmar una reserva, Django solo publica la tarea
  `send_reservation_confirmation` en Redis (`CeleryNotifier`) y responde de inmediato. El
  worker la entrega al microservicio de notificaciones y, si este está caído, reintenta con
  espera exponencial (5 s, 10 s, 20 s... hasta 6 intentos). Si Redis no responde, la
  notificación se envía en el momento para que el huésped no se quede sin ella.
- **Reportes.** `POST /api/v1/reports/occupancy/` encola `generate_occupancy_report`
  (ocupación e ingresos de un rango de fechas) y responde 202 con un `task_id`. El
  resultado se consulta en `GET /api/v1/reports/<task_id>/`. Solo para usuarios staff:
  inicia sesión en `/admin/` y usa la API navegable.

## Patrones de diseño

- **Builder** — `ReservationBuilder` ensambla y valida la reserva, la entidad más compleja del
  sistema, y devuelve un agregado sin persistir para que el servicio controle la transacción.
- **Factory** — `NotifierFactory` y `PaymentGatewayFactory` resuelven qué implementación de
  notificador y de pasarela construir según la configuración del entorno.

## Tecnologías

- Python 3.11
- Django 5.2
- Django Rest Framework 3.18
- Flask 3.1 + gunicorn (microservicios de cotización, catálogo, pagos y notificaciones)
- PostgreSQL 17 (SQLite solo para correr Django sin Docker)
- Nginx 1.30
- Redis 8 + Celery 5.7 (tareas asíncronas)
- Docker y Docker Compose
- HTML semántico

## Puesta en marcha con Docker

Levanta Django, los cuatro microservicios Flask, Nginx, Redis y el worker de Celery juntos. Requiere Docker Desktop.
Copia `.env.example` como `.env` y define `SECRET_KEY` e `INTERNAL_API_TOKEN`.

```bash
docker compose up --build
```

Abre `http://localhost`. Las migraciones y los datos de ejemplo (`seed`) se cargan solos al
arrancar el contenedor de Django, y los datos de PostgreSQL se guardan en el volumen `postgres_data`.
Para entrar al administrador, crea el superusuario dentro del contenedor (no ejecutes este
comando solamente en tu Python local, porque eso usa otra base de datos):

```bash
docker compose exec django_web python manage.py createsuperuser
```

Después abre `http://localhost/admin/`. El usuario debe tener `is_staff` e `is_superuser`;
crear un usuario en el host no lo crea automáticamente en PostgreSQL.

| Comando | Para qué |
|---|---|
| `docker compose up -d --build` | Levantar en segundo plano |
| `docker compose logs -f` | Ver los logs de todos los servicios |
| `docker compose restart nginx` | Recargar tras editar `nginx/nginx.conf` |
| `docker compose down` | Detener y borrar contenedores |
| `docker compose down -v` | Además, borrar las bases de datos |

Si el puerto 80 está ocupado, cambia `"80:80"` por `"8080:80"` en `docker-compose.yml`.

## Despliegue en AWS Academy (EC2)

Django corre con **gunicorn** y `DEBUG=False`; los estáticos (CSS, JS y fotos
de `web/static/web/img/`) se agrupan con `collectstatic` al construir la imagen
y los sirve WhiteNoise. Las fotos subidas (`/media/`) las sirve Nginx.

1. Instancia Ubuntu `t3.small` o mayor. Security Group: 22 (tu IP) y 80 (0.0.0.0/0).
2. Asocia una **IP elástica** a la instancia.
3. En la instancia:
   ```bash
   sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
   sudo usermod -aG docker $USER && newgrp docker
   git clone <url-del-repo> && cd ArquitecturaDeSoftware-Proyecto
   cp .env.example .env   # pon la IP elástica y secretos reales
   docker compose up -d --build
   ```
4. En `.env`, la IP elástica va en `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`
   (`http://<IP>`) y `PUBLIC_BASE_URL` (`http://<IP>`).

API pública para el equipo aliado (GET, con CORS habilitado):
`http://<IP>/api/v1/rooms/?page=1&page_size=12`

## Puesta en marcha sin Docker

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

python manage.py migrate
python manage.py loaddata seed
python manage.py runserver
```

Cada microservicio se arranca en su propia terminal con `pip install -r requirements.txt`
y `python app.py` dentro de su carpeta:

| Carpeta | Puerto |
|---|---|
| `pricing_service/` | 5000 |
| `catalog_service/` | 5001 |
| `payment_service/` | 5002 |
| `notification_service/` | 5003 |

Los tres últimos necesitan PostgreSQL. Lo más simple es levantar solo la base con
`docker compose up -d postgres` y apuntar cada servicio con la variable `DATABASE_URL`
(ver el `config.py` de cada uno).

Sin Docker, Django usa por defecto la pasarela simulada y el notificador de consola. Para probar Celery
en local necesitas un Redis en `localhost:6379`, `NOTIFIER_TYPE=CELERY` y un worker:
`celery -A hotelMDJ worker -l info --pool=solo` (`--pool=solo` en Windows). Para que
use los microservicios, define `PAYMENT_GATEWAY_TYPE=HTTP` y `NOTIFIER_TYPE=HTTP` en `.env`.

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
| `GET` | `/api/v1/rooms/?page=1&page_size=12` | 200 (catálogo público paginado, máximo 12 por página) |
| `GET` | `/api/v1/rooms/available/` | 200, 400 (servido por `catalog_service`) |
| `POST` | `/api/v1/reservations/` | 201, 400, 402, 404, 409 |
| `POST` | `/api/v1/reservations/lookup/` | 200, 400, 404 |
| `POST` | `/api/v1/reports/occupancy/` (staff) | 202, 400, 403, 503 |
| `GET` | `/api/v1/reports/<task_id>/` (staff) | 200, 403 |

### API v2 (microservicios Flask)

| Método | Ruta | Códigos |
|---|---|---|
| `GET` | `/api/v2/cotizacion/health/` | 200 |
| `POST` | `/api/v2/cotizacion/` | 200, 400, 405, 500 |
| `GET` | `/api/v2/catalogo/health/` | 200 |
| `GET` | `/api/v2/pagos/health/` | 200 |
| `POST` | `/api/v2/pagos/` (interno) | 201, 400, 402, 403 |
| `GET` | `/api/v2/pagos/<referencia>/` | 200, 404 |
| `GET` | `/api/v2/notificaciones/health/` | 200 |
| `POST` | `/api/v2/notificaciones/` (interno) | 201, 400, 403, 502 |
| `GET` | `/api/v2/notificaciones/<codigo>/` | 200, 404 (correo enmascarado) |

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

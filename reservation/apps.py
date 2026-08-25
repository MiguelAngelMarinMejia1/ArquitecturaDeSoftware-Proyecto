from django.apps import AppConfig


class ReservationConfig(AppConfig):
    """Business core of Hotel MDJ: domain entities, policies, services and API.

    This app knows nothing about HTML rendering. It is consumed both by the
    `web` app (server-rendered pages) and by its own DRF layer (`reservation.api`).
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "reservation"
    verbose_name = "Reservas"

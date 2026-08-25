from django.apps import AppConfig


class WebConfig(AppConfig):
    """HTML presentation layer for Hotel MDJ.

    Holds only templates, static assets and thin views. Every business
    decision is delegated to `reservation.services`.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "web"
    verbose_name = "Sitio web"

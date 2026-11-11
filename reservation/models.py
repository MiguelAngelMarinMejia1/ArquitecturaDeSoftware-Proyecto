"""Persistence entities for the Hotel MDJ booking core.

These classes are deliberately *anemic*: they declare fields, constraints,
choices and a readable ``__str__`` -- nothing else. Every business rule
(pricing, availability, capacity, state transitions) lives in the domain and
service layers, so that no calculation or validation ever hides inside a model
method.

Mapping to the UML class diagram:

===============================  =====================================
UML operation                    Implemented in
===============================  =====================================
Reserva.calcularTotal()          domain.policies.PricingPolicy
Habitacion.verificarDisponib.()  selectors.available_rooms()
TipoHab.calcularPrecioTemporada  domain.policies.SeasonalPricingPolicy
Reserva.confirmar() / cancelar() services.ReservationService
Cliente.registrarse()            services.CustomerService
Pago.procesarPago()              services.PaymentService
Factura.generarFactura()         services.InvoiceService
===============================  =====================================
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _


class Customer(models.Model):
    """A guest profile.

    Modelled after real Property Management Systems (Oracle OPERA, Cloudbeds):
    the profile is a first-class entity that exists from the moment someone
    books, whether or not they ever create an account.

    ``user`` is the single, optional bridge to Django's authentication system.
    A guest booking leaves it NULL; when that person later registers with the
    same e-mail, the account is linked here and inherits the whole booking
    history without migrating any data. Hotel staff, conversely, have a ``User``
    and no ``Customer``.

    ``email`` is the natural key used to de-duplicate returning guests.
    ``document_id`` stays optional on purpose: identity documents are collected
    at physical check-in, not during online booking (data minimisation).
    """

    first_name = models.CharField(_("nombres"), max_length=100)
    last_name = models.CharField(_("apellidos"), max_length=100)
    email = models.EmailField(_("correo electronico"), unique=True)
    phone = models.CharField(_("telefono"), max_length=30)
    country = models.CharField(_("pais"), max_length=60, blank=True)
    document_id = models.CharField(
        _("documento de identidad"),
        max_length=30,
        null=True,
        blank=True,
        help_text=_("Se captura en el check-in presencial, no al reservar."),
    )
    marketing_consent = models.BooleanField(
        _("acepta comunicaciones comerciales"),
        default=False,
        help_text=_("Opt-in explicito e independiente de la reserva."),
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customer_profile",
        verbose_name=_("cuenta de usuario"),
        help_text=_("Vacio mientras el huesped no tenga cuenta registrada."),
    )
    created_at = models.DateTimeField(_("fecha de registro"), auto_now_add=True)

    class Meta:
        verbose_name = _("cliente")
        verbose_name_plural = _("clientes")
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class RoomType(models.Model):
    """A category of room (Standard, Suite, ...) with its base rate."""

    name = models.CharField(_("nombre"), max_length=60, unique=True)
    description = models.TextField(_("descripcion"), blank=True)
    max_capacity = models.PositiveSmallIntegerField(_("capacidad maxima"))
    bed_type = models.CharField(_("tipo de cama"), max_length=60, blank=True)
    base_price_per_night = models.DecimalField(
        _("precio base por noche"), max_digits=12, decimal_places=2
    )

    class Meta:
        verbose_name = _("tipo de habitacion")
        verbose_name_plural = _("tipos de habitacion")
        ordering = ["base_price_per_night"]

    def __str__(self):
        return self.name


class Room(models.Model):
    """A physical room.

    Availability is never stored here: it is derived from overlapping
    reservations in ``selectors.available_rooms()``. A stored flag would go
    stale the moment a booking is cancelled.
    """

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", _("Disponible")
        OCCUPIED = "OCCUPIED", _("Ocupada")
        MAINTENANCE = "MAINTENANCE", _("En mantenimiento")

    number = models.CharField(_("numero"), max_length=10, unique=True)
    floor = models.PositiveSmallIntegerField(_("piso"))
    status = models.CharField(
        _("estado"), max_length=20, choices=Status.choices, default=Status.AVAILABLE
    )
    room_type = models.ForeignKey(
        RoomType,
        on_delete=models.PROTECT,
        related_name="rooms",
        verbose_name=_("tipo de habitacion"),
    )
    image_urls = models.TextField(
        _("URLs de imagenes"),
        blank=True,
        help_text=_("URLs separadas por comas, en el orden de la galeria."),
    )
    is_active = models.BooleanField(_("activa"), default=True)

    class Meta:
        verbose_name = _("habitacion")
        verbose_name_plural = _("habitaciones")
        ordering = ["floor", "number"]

    def __str__(self):
        return gettext("Habitación %(number)s - %(room_type)s") % {
            "number": self.number,
            "room_type": self.room_type.name,
        }


class Reservation(models.Model):
    """A booking made by a customer for one or more rooms.

    Amounts are stored (not recomputed on read) because a reservation is a
    commercial commitment: if the rate or the tax percentage changes tomorrow,
    what the guest agreed to pay must not change with it.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", _("Pendiente")
        CONFIRMED = "CONFIRMED", _("Confirmada")
        CANCELLED = "CANCELLED", _("Cancelada")

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="reservations",
        verbose_name=_("cliente"),
    )
    rooms = models.ManyToManyField(
        Room,
        through="ReservationRoom",
        related_name="reservations",
        verbose_name=_("habitaciones"),
    )
    check_in_date = models.DateField(_("fecha de entrada"))
    check_out_date = models.DateField(_("fecha de salida"))
    num_adults = models.PositiveSmallIntegerField(_("adultos"), default=1)
    num_children = models.PositiveSmallIntegerField(_("ninos"), default=0)
    special_requests = models.TextField(_("solicitudes especiales"), blank=True)
    status = models.CharField(
        _("estado"), max_length=20, choices=Status.choices, default=Status.PENDING
    )
    confirmation_code = models.CharField(
        _("codigo de confirmacion"), max_length=20, unique=True, db_index=True
    )
    subtotal = models.DecimalField(_("subtotal"), max_digits=12, decimal_places=2)
    taxes = models.DecimalField(_("impuestos"), max_digits=12, decimal_places=2)
    total_amount = models.DecimalField(_("total"), max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(_("fecha de creacion"), auto_now_add=True)

    class Meta:
        verbose_name = _("reserva")
        verbose_name_plural = _("reservas")
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(check_out_date__gt=models.F("check_in_date")),
                name="reservation_checkout_after_checkin",
            ),
        ]

    def __str__(self):
        return gettext("Reserva %(code)s") % {"code": self.confirmation_code}


class ReservationRoom(models.Model):
    """Materialises the ``1..*`` association between Reservation and Room.

    ``price_per_night`` is frozen at booking time so that later rate changes
    never rewrite the price a guest was quoted.
    """

    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        related_name="reservation_rooms",
        verbose_name=_("reserva"),
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.PROTECT,
        related_name="reservation_rooms",
        verbose_name=_("habitacion"),
    )
    price_per_night = models.DecimalField(
        _("precio por noche"), max_digits=12, decimal_places=2
    )

    class Meta:
        verbose_name = _("habitacion reservada")
        verbose_name_plural = _("habitaciones reservadas")
        constraints = [
            models.UniqueConstraint(
                fields=["reservation", "room"],
                name="unique_room_per_reservation",
            ),
        ]

    def __str__(self):
        return gettext("%(room)s en %(reservation)s") % {
            "room": self.room,
            "reservation": self.reservation,
        }


class Payment(models.Model):
    """A payment associated with a single reservation."""

    class Method(models.TextChoices):
        CREDIT_CARD = "CREDIT_CARD", _("Tarjeta de credito")
        DEBIT_CARD = "DEBIT_CARD", _("Tarjeta debito")
        CASH = "CASH", _("Efectivo")
        TRANSFER = "TRANSFER", _("Transferencia bancaria")

    class Status(models.TextChoices):
        PENDING = "PENDING", _("Pendiente")
        COMPLETED = "COMPLETED", _("Completado")
        FAILED = "FAILED", _("Fallido")
        REFUNDED = "REFUNDED", _("Reembolsado")

    reservation = models.OneToOneField(
        Reservation,
        on_delete=models.CASCADE,
        related_name="payment",
        verbose_name=_("reserva"),
    )
    amount = models.DecimalField(_("monto"), max_digits=12, decimal_places=2)
    date = models.DateTimeField(_("fecha"), auto_now_add=True)
    payment_method = models.CharField(
        _("metodo de pago"), max_length=20, choices=Method.choices
    )
    status = models.CharField(
        _("estado"), max_length=20, choices=Status.choices, default=Status.PENDING
    )
    gateway_reference = models.CharField(
        _("referencia de la pasarela"),
        max_length=60,
        blank=True,
        help_text=_("Identificador devuelto por la pasarela de pago."),
    )

    class Meta:
        verbose_name = _("pago")
        verbose_name_plural = _("pagos")
        ordering = ["-date"]

    def __str__(self):
        return gettext("Pago de %(reservation)s") % {"reservation": self.reservation}


class Invoice(models.Model):
    """An invoice issued once a payment is completed."""

    payment = models.OneToOneField(
        Payment,
        on_delete=models.CASCADE,
        related_name="invoice",
        verbose_name=_("pago"),
    )
    issue_date = models.DateTimeField(_("fecha de emision"), auto_now_add=True)
    subtotal = models.DecimalField(_("subtotal"), max_digits=12, decimal_places=2)
    taxes = models.DecimalField(_("impuestos"), max_digits=12, decimal_places=2)
    total = models.DecimalField(_("total"), max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = _("factura")
        verbose_name_plural = _("facturas")
        ordering = ["-issue_date"]

    def __str__(self):
        return gettext("Factura de %(reservation)s") % {
            "reservation": self.payment.reservation
        }

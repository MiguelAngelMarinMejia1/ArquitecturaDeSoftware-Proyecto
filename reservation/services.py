"""Application service layer.

This is the only place where a business flow is orchestrated. Views -- whether
they render HTML or return JSON -- read the request, hand a plain dictionary to
a service and present whatever comes back. They never calculate, never
validate business rules and never decide which collaborator to build.

Every service receives its collaborators through the constructor, with a
factory supplying the default. That is what makes them *injectable*: a test can
pass a fake notifier or gateway without touching configuration, and a new
implementation never requires editing these classes (Dependency Inversion).
"""

from django.db import transaction

from reservation.domain.builders import ReservationBuilder
from reservation.domain.codes import ConfirmationCodeGenerator
from reservation.domain.exceptions import (
    PaymentDeclinedError,
    ReservationNotFoundError,
    RoomNotFoundError,
)
from reservation.domain.policies import PricingPolicy
from reservation.infra.factories import NotifierFactory, PaymentGatewayFactory
from reservation.models import (
    Customer,
    Invoice,
    Payment,
    Reservation,
    ReservationRoom,
    Room,
)
from reservation.selectors import find_reservation


class CustomerService:
    """Resolves the guest profile behind a booking.

    UML origin: ``Cliente.registrarse()``.

    The profile is keyed by e-mail, so a returning guest reuses the record they
    already have instead of creating a duplicate. Contact details are refreshed
    on each booking because the most recent booking carries the most current
    phone number. ``user`` is never touched here: linking a profile to an
    account is a separate, deliberate action.
    """

    PROFILE_FIELDS = ("first_name", "last_name", "phone", "country")

    def get_or_create_profile(self, data: dict) -> Customer:
        email = (data.get("email") or "").strip().lower()

        customer, created = Customer.objects.get_or_create(
            email=email,
            defaults={
                "first_name": (data.get("first_name") or "").strip(),
                "last_name": (data.get("last_name") or "").strip(),
                "phone": (data.get("phone") or "").strip(),
                "country": (data.get("country") or "").strip(),
                "marketing_consent": bool(data.get("marketing_consent")),
            },
        )

        if not created:
            for field in self.PROFILE_FIELDS:
                value = (data.get(field) or "").strip()
                if value:
                    setattr(customer, field, value)
            # Consent is only ever granted here, never silently revoked by a
            # booking form the guest left unchecked.
            if data.get("marketing_consent"):
                customer.marketing_consent = True
            customer.save()

        return customer

    def link_to_account(self, customer: Customer, user) -> Customer:
        """Attach a freshly registered account to an existing guest profile.

        Not reachable from the UI yet -- it is the hook that lets a guest who
        booked without an account keep their history when they register later.
        """
        customer.user = user
        customer.save(update_fields=["user"])
        return customer


class PaymentService:
    """Charges a reservation through the configured gateway.

    UML origin: ``Pago.procesarPago()``.
    """

    def __init__(self, gateway=None):
        self._gateway = gateway or PaymentGatewayFactory.create()

    def charge(self, reservation: Reservation, payment_method: str) -> Payment:
        result = self._gateway.charge(
            amount=reservation.total_amount,
            method=payment_method,
            reference_hint=reservation.confirmation_code,
        )

        payment = Payment.objects.create(
            reservation=reservation,
            amount=reservation.total_amount,
            payment_method=payment_method,
            status=(
                Payment.Status.COMPLETED if result.approved else Payment.Status.FAILED
            ),
            gateway_reference=result.reference,
        )

        if not result.approved:
            raise PaymentDeclinedError(result.message or "El pago fue rechazado.")

        return payment


class InvoiceService:
    """Issues the invoice for a completed payment.

    UML origin: ``Factura.generarFactura()``.
    """

    def issue(self, payment: Payment) -> Invoice:
        reservation = payment.reservation
        return Invoice.objects.create(
            payment=payment,
            subtotal=reservation.subtotal,
            taxes=reservation.taxes,
            total=reservation.total_amount,
        )


class ReservationService:
    """Orchestrates the full 'create reservation' flow."""

    def __init__(
        self,
        notifier=None,
        customer_service=None,
        payment_service=None,
        invoice_service=None,
        pricing_policy=None,
        code_generator=None,
    ):
        self._notifier = notifier or NotifierFactory.create()
        self._customers = customer_service or CustomerService()
        self._payments = payment_service or PaymentService()
        self._invoices = invoice_service or InvoiceService()
        self._pricing = pricing_policy or PricingPolicy()
        self._codes = code_generator or ConfirmationCodeGenerator()

    # --- Commands ---------------------------------------------------------

    @transaction.atomic
    def create_reservation(self, data: dict) -> Reservation:
        """Create, charge and confirm a reservation.

        The whole flow runs in one transaction: if the payment is declined or
        any invariant fails, no half-written reservation survives. The guest is
        notified only after the transaction commits, so a failed e-mail can
        never roll back a paid booking.
        """
        customer = self._customers.get_or_create_profile(data)
        rooms = self._resolve_rooms(data.get("room_ids") or [])

        code = self._codes.generate_unique(
            lambda candidate: Reservation.objects.filter(
                confirmation_code=candidate
            ).exists()
        )

        draft = (
            ReservationBuilder(pricing_policy=self._pricing)
            .for_customer(customer)
            .add_rooms(rooms)
            .with_dates(data["check_in_date"], data["check_out_date"])
            .with_guests(data.get("num_adults"), data.get("num_children", 0))
            .with_special_requests(data.get("special_requests", ""))
            .with_confirmation_code(code)
            .build()
        )

        reservation = draft.reservation
        reservation.save()

        for line in draft.room_lines:
            line.reservation = reservation
        ReservationRoom.objects.bulk_create(draft.room_lines)

        payment = self._payments.charge(
            reservation, data.get("payment_method") or "CREDIT_CARD"
        )
        self._invoices.issue(payment)

        reservation.status = Reservation.Status.CONFIRMED
        reservation.save(update_fields=["status"])

        transaction.on_commit(lambda: self._notifier.send_confirmation(reservation))
        return reservation

    def cancel_reservation(self, reservation: Reservation) -> Reservation:
        """UML origin: ``Reserva.cancelar()``."""
        reservation.status = Reservation.Status.CANCELLED
        reservation.save(update_fields=["status"])
        return reservation

    # --- Queries ----------------------------------------------------------

    def quote(self, rooms, check_in, check_out):
        """Price a tentative selection without committing to anything.

        Used by the booking page to show what a stay would cost before the
        guest fills in their details, so the same pricing rules drive both the
        estimate and the final charge.
        """
        return self._pricing.quote(rooms, check_in, check_out)

    def lookup(self, confirmation_code: str, email: str) -> Reservation:
        reservation = find_reservation(confirmation_code, email)
        if reservation is None:
            raise ReservationNotFoundError(
                "No encontramos una reserva con ese codigo y correo electronico."
            )
        return reservation

    def lookup_by_code(self, confirmation_code: str) -> Reservation:
        """Retrieve a booking by code alone.

        Reserved for the moment right after checkout, where the caller has
        already proven ownership by having just created the reservation. Every
        other path must go through :meth:`lookup`, which also demands the
        e-mail address.
        """
        reservation = (
            Reservation.objects.select_related("customer")
            .prefetch_related("reservation_rooms__room__room_type")
            .filter(confirmation_code=confirmation_code)
            .first()
        )
        if reservation is None:
            raise ReservationNotFoundError(
                "No encontramos una reserva con ese codigo."
            )
        return reservation

    # --- Internals --------------------------------------------------------

    @staticmethod
    def _resolve_rooms(room_ids):
        """Load the selected rooms, failing loudly if any does not exist."""
        rooms = list(
            Room.objects.filter(pk__in=room_ids).select_related("room_type")
        )
        found = {room.pk for room in rooms}
        missing = [str(rid) for rid in room_ids if int(rid) not in found]
        if missing:
            raise RoomNotFoundError(
                "No existe la habitacion con id " + ", ".join(missing) + "."
            )
        return rooms

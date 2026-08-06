from django.db import models


class Customer(models.Model):
    """Represents a person who can make hotel room reservations."""
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    document_id = models.CharField(max_length=30, unique=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class RoomType(models.Model):
    """Defines a category of room (e.g. Standard, Suite) with base pricing."""
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    max_capacity = models.PositiveIntegerField()
    base_price_per_night = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.name


class Room(models.Model):
    """A physical room. Availability is resolved via reservation overlap,
    not stored as a static field, to avoid stale/inconsistent state."""

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        OCCUPIED = "OCCUPIED", "Occupied"
        MAINTENANCE = "MAINTENANCE", "Maintenance"

    number = models.CharField(max_length=10)
    floor = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.AVAILABLE
    )
    room_type = models.ForeignKey(
        RoomType, on_delete=models.PROTECT, related_name="rooms"
    )

    def __str__(self):
        return f"Room {self.number} ({self.room_type})"


class Reservation(models.Model):
    """A booking made by a customer for a room. Business rules (date validation,
    total calculation, confirmation flow) live in the domain/service layers,
    not here."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        CANCELLED = "CANCELLED", "Cancelled"

    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="reservations"
    )
    room = models.ForeignKey(
        Room, on_delete=models.PROTECT, related_name="reservations"
    )
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    creation_date = models.DateTimeField(auto_now_add=True)
    num_guests = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )

    def __str__(self):
        return f"Reservation #{self.id} - {self.customer}"


class Payment(models.Model):
    """A payment associated with a single reservation."""

    class Method(models.TextChoices):
        CREDIT_CARD = "CREDIT_CARD", "Credit Card"
        CASH = "CASH", "Cash"
        TRANSFER = "TRANSFER", "Bank Transfer"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        COMPLETED = "COMPLETED", "Completed"
        REFUNDED = "REFUNDED", "Refunded"

    reservation = models.OneToOneField(
        Reservation, on_delete=models.CASCADE, related_name="payment"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=20, choices=Method.choices)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )

    def __str__(self):
        return f"Payment #{self.id} for Reservation #{self.reservation_id}"


class Invoice(models.Model):
    """An invoice generated once a payment is completed."""
    payment = models.OneToOneField(
        Payment, on_delete=models.CASCADE, related_name="invoice"
    )
    issue_date = models.DateTimeField(auto_now_add=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    taxes = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Invoice #{self.id}"
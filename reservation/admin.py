"""Admin registrations for back-office access to the booking data."""

from django.contrib import admin

from reservation.models import (
    Customer,
    Invoice,
    Payment,
    Reservation,
    ReservationRoom,
    Room,
    RoomType,
)


class ReservationRoomInline(admin.TabularInline):
    model = ReservationRoom
    extra = 0
    autocomplete_fields = ["room"]


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ["last_name", "first_name", "email", "phone", "has_account"]
    list_filter = ["marketing_consent", "country"]
    search_fields = ["first_name", "last_name", "email", "document_id"]
    readonly_fields = ["created_at"]

    @admin.display(boolean=True, description="cuenta registrada")
    def has_account(self, obj):
        return obj.user_id is not None


@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "max_capacity", "bed_type", "base_price_per_night"]
    search_fields = ["name"]


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ["number", "floor", "room_type", "status", "is_active"]
    list_filter = ["status", "is_active", "room_type"]
    search_fields = ["number"]


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = [
        "confirmation_code",
        "customer",
        "check_in_date",
        "check_out_date",
        "status",
        "total_amount",
    ]
    list_filter = ["status", "check_in_date"]
    search_fields = ["confirmation_code", "customer__email", "customer__last_name"]
    # Amounts are the commercial record of what the guest agreed to pay and are
    # produced by the pricing policy, so they are not editable by hand here.
    readonly_fields = ["confirmation_code", "subtotal", "taxes", "total_amount", "created_at"]
    inlines = [ReservationRoomInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["reservation", "amount", "payment_method", "status", "date"]
    list_filter = ["status", "payment_method"]
    search_fields = ["reservation__confirmation_code", "gateway_reference"]
    readonly_fields = ["date"]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ["payment", "issue_date", "subtotal", "taxes", "total"]
    readonly_fields = ["issue_date"]

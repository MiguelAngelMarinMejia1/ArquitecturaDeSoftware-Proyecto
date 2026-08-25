"""Serializers for the reservation API.

Input and output are separate classes on purpose. An input serializer answers
"is this payload well-formed?" and nothing else -- it never decides whether a
room is free or how much a stay costs, because that is a business rule and it
belongs in the domain layer. Output serializers shape what leaves the system,
including how much personal data a given endpoint is allowed to reveal.
"""

from rest_framework import serializers

from reservation.models import (
    Customer,
    Payment,
    Reservation,
    ReservationRoom,
    Room,
    RoomType,
)


class RoomTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomType
        fields = [
            "id",
            "name",
            "description",
            "max_capacity",
            "bed_type",
            "base_price_per_night",
        ]


class RoomSerializer(serializers.ModelSerializer):
    room_type = RoomTypeSerializer(read_only=True)

    class Meta:
        model = Room
        fields = ["id", "number", "floor", "status", "room_type"]


class AvailabilityQuerySerializer(serializers.Serializer):
    """Validates the query string of the availability endpoint.

    Only non-personal search criteria travel here, which is why these values
    are safe to carry in a URL.
    """

    check_in = serializers.DateField()
    check_out = serializers.DateField()
    adults = serializers.IntegerField(min_value=1, default=1)
    children = serializers.IntegerField(min_value=0, default=0)
    room_type = serializers.PrimaryKeyRelatedField(
        queryset=RoomType.objects.all(), required=False, allow_null=True
    )

    def validate(self, attrs):
        if attrs["check_out"] <= attrs["check_in"]:
            raise serializers.ValidationError(
                {"check_out": "La fecha de salida debe ser posterior a la de entrada."}
            )
        return attrs


class CustomerReadSerializer(serializers.ModelSerializer):
    """Guest data as returned by the API.

    ``document_id`` is absent by design: it is not collected during online
    booking, and an endpoint reachable with a confirmation code should not be
    able to hand out identity documents.
    """

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = ["full_name", "email", "phone", "country"]

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"


class ReservationRoomSerializer(serializers.ModelSerializer):
    room = RoomSerializer(read_only=True)

    class Meta:
        model = ReservationRoom
        fields = ["room", "price_per_night"]


class ReservationReadSerializer(serializers.ModelSerializer):
    customer = CustomerReadSerializer(read_only=True)
    reservation_rooms = ReservationRoomSerializer(many=True, read_only=True)
    nights = serializers.SerializerMethodField()

    class Meta:
        model = Reservation
        fields = [
            "confirmation_code",
            "status",
            "customer",
            "reservation_rooms",
            "check_in_date",
            "check_out_date",
            "nights",
            "num_adults",
            "num_children",
            "special_requests",
            "subtotal",
            "taxes",
            "total_amount",
            "created_at",
        ]

    def get_nights(self, obj):
        return (obj.check_out_date - obj.check_in_date).days


class ReservationCreateSerializer(serializers.Serializer):
    """Validates the booking payload.

    Guest details arrive in the request body, never in the query string:
    URLs end up in browser history, server and proxy access logs and the
    ``Referer`` header sent to third parties.
    """

    check_in_date = serializers.DateField()
    check_out_date = serializers.DateField()
    room_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )
    num_adults = serializers.IntegerField(min_value=1)
    num_children = serializers.IntegerField(min_value=0, default=0)
    special_requests = serializers.CharField(
        required=False, allow_blank=True, default=""
    )

    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=30)
    country = serializers.CharField(max_length=60, required=False, allow_blank=True)
    marketing_consent = serializers.BooleanField(default=False)

    payment_method = serializers.ChoiceField(
        choices=Payment.Method.choices,
        default=Payment.Method.CREDIT_CARD,
    )


class ReservationLookupSerializer(serializers.Serializer):
    """Credentials a guest without an account presents to see their booking.

    The e-mail is required alongside the code so that a leaked or guessed code
    is not enough on its own to expose someone's data.
    """

    confirmation_code = serializers.CharField(max_length=20)
    email = serializers.EmailField()

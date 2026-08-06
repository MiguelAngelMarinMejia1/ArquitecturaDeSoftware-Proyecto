# reservation/domain/exceptions.py
"""Domain-specific exceptions for the reservation creation flow.
Using named exceptions (instead of generic ValueError) lets the service/view
layer catch and handle each failure case distinctly."""


class ReservationDomainError(Exception):
    """Base exception for all reservation domain errors."""
    pass


class IncompleteReservationDataError(ReservationDomainError):
    """Raised when build() is called before all required fields were set."""
    pass


class InvalidDateRangeError(ReservationDomainError):
    """Raised when check_in_date is not strictly before check_out_date."""
    pass


class RoomNotAvailableError(ReservationDomainError):
    """Raised when the selected room has an overlapping reservation
    in the requested date range."""
    pass


class GuestCapacityExceededError(ReservationDomainError):
    """Raised when num_guests exceeds the room type's max_capacity."""
    pass
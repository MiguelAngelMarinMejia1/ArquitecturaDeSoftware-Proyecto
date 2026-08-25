"""Domain-specific exceptions for the reservation flow.

Named exceptions (instead of a generic ``ValueError``) let every layer above
react to each failure distinctly. In particular
``reservation.api.exception_handler`` maps each class to the HTTP status code
the assignment requires, which is why the APIViews need no business-level
``try/except`` of their own.

    IncompleteReservationDataError  -> 400
    InvalidDateRangeError           -> 400
    GuestCapacityExceededError      -> 400
    NoRoomsSelectedError            -> 400
    RoomNotFoundError               -> 404
    ReservationNotFoundError        -> 404
    RoomNotAvailableError           -> 409
"""


class ReservationDomainError(Exception):
    """Base class for every business rule violation in this bounded context."""


# --- 400 Bad Request ------------------------------------------------------


class IncompleteReservationDataError(ReservationDomainError):
    """``build()`` was called before every required field had been set."""


class InvalidDateRangeError(ReservationDomainError):
    """Check-out is not strictly after check-in, or the range is in the past."""


class GuestCapacityExceededError(ReservationDomainError):
    """More guests than the combined capacity of the selected rooms."""


class NoRoomsSelectedError(ReservationDomainError):
    """A reservation needs at least one room (UML multiplicity ``1..*``)."""


# --- 404 Not Found --------------------------------------------------------


class RoomNotFoundError(ReservationDomainError):
    """A referenced room does not exist or is not bookable."""


class ReservationNotFoundError(ReservationDomainError):
    """No reservation matches the given confirmation code and e-mail."""


# --- 409 Conflict ---------------------------------------------------------


class RoomNotAvailableError(ReservationDomainError):
    """The room is already booked for an overlapping date range."""


# --- Payment --------------------------------------------------------------


class PaymentDeclinedError(ReservationDomainError):
    """The payment gateway rejected the charge."""

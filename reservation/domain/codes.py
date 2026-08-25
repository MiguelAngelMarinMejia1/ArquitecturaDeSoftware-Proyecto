"""Generation of reservation confirmation codes.

The code is what lets a guest reach their booking without an account, so it
must not be guessable by counting: sequential ids would let anyone enumerate
other people's reservations. ``secrets`` provides a cryptographically strong
source, and the alphabet drops characters that are easy to misread aloud or
over the phone (0/O, 1/I).
"""

import secrets

from django.conf import settings

# Crockford-style alphabet: no 0, O, 1, I to avoid transcription mistakes.
ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"

CODE_LENGTH = 8


class ConfirmationCodeGenerator:
    """Builds unique, non-sequential confirmation codes.

    Uniqueness is enforced by the database (``Reservation.confirmation_code``
    is ``unique``); this generator only has to make collisions improbable.
    With a 32-character alphabet and 8 positions there are 32**8 possibilities,
    so a retry loop of a few attempts is more than enough.
    """

    def __init__(self, prefix: str | None = None, length: int = CODE_LENGTH):
        self._prefix = prefix if prefix is not None else settings.CONFIRMATION_CODE_PREFIX
        self._length = length

    def generate(self) -> str:
        body = "".join(secrets.choice(ALPHABET) for _ in range(self._length))
        return f"{self._prefix}-{body}"

    def generate_unique(self, exists, max_attempts: int = 10) -> str:
        """Generate a code that ``exists(code)`` reports as unused.

        ``exists`` is injected rather than querying the ORM here, so the domain
        layer stays free of persistence concerns and the generator can be
        tested without a database.
        """
        for _ in range(max_attempts):
            code = self.generate()
            if not exists(code):
                return code
        raise RuntimeError(
            "No se pudo generar un codigo de confirmacion unico "
            f"tras {max_attempts} intentos."
        )

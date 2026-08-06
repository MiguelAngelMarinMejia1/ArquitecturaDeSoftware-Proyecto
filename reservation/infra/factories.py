"""Factory for infrastructure dependencies."""

import os

from reservation.infra.notifications import (
    ConsoleNotifier,
    EmailNotifier,
)


class NotifierFactory:
    """Creates the appropriate notifier implementation based on the
    environment configuration.
    """

    @staticmethod
    def create(notifier_type=None):
        notifier_type = (
            notifier_type or os.getenv("NOTIFIER_TYPE", "CONSOLE")
        ).upper()

        if notifier_type == "EMAIL":
            return EmailNotifier()

        return ConsoleNotifier()
"""Delivery channels (moved from ``reservation/infra/notifications.py``).

Each channel returns ``(sent: bool, error: str)`` and never raises: a bounced
e-mail must not break the caller.
"""

import logging
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def render_confirmation(data):
    subject = f"Hotel MDJ - Reserva {data['confirmation_code']}"
    body = (
        f"Hola {data['recipient_name']},\n\n"
        f"Tu reserva {data['confirmation_code']} quedó registrada.\n"
        f"Entrada: {data['check_in_date']}\n"
        f"Salida: {data['check_out_date']}\n"
        f"Total: {data['total_amount']}\n\n"
        "Hotel MDJ"
    )
    return subject, body


class ConsoleChannel:
    NAME = "CONSOLE"

    def __init__(self, config):
        pass

    def send(self, to, subject, body):
        print(f"[NOTIFICATION] To: {to} | {subject}\n{body}", flush=True)
        return True, ""


class EmailChannel:
    NAME = "EMAIL"

    def __init__(self, config):
        self._config = config

    def send(self, to, subject, body):
        message = EmailMessage()
        message["From"] = self._config["MAIL_FROM"]
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        try:
            with smtplib.SMTP(
                self._config["SMTP_HOST"], self._config["SMTP_PORT"], timeout=10
            ) as smtp:
                if self._config["SMTP_USE_TLS"]:
                    smtp.starttls()
                if self._config["SMTP_USER"]:
                    smtp.login(self._config["SMTP_USER"], self._config["SMTP_PASSWORD"])
                smtp.send_message(message)
            return True, ""
        except (OSError, smtplib.SMTPException) as exc:
            logger.error("Could not send e-mail to %s: %s", to, exc)
            return False, str(exc)


_CHANNELS = {ConsoleChannel.NAME: ConsoleChannel, EmailChannel.NAME: EmailChannel}


def build_channel(config):
    # Unknown value -> console: the guest's notification is never just dropped.
    channel_class = _CHANNELS.get(config["CHANNEL"].upper(), ConsoleChannel)
    return channel_class(config)

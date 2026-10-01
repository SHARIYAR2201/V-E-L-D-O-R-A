"""Dev mailer: logs messages and keeps them in OUTBOX (used by tests). Replace send() with SMTP/SES in production."""
import logging
OUTBOX: list[dict] = []
log = logging.getLogger("veldora.mail")


def send(to: str, subject: str, body: str):
    OUTBOX.append({"to": to, "subject": subject, "body": body})
    log.info("MAIL to=%s subject=%s", to, subject)

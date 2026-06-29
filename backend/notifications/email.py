"""Pluggable email delivery (Phase 3).

Kept behind one interface so the project does not hard-couple to any vendor:
the dev default just logs (``ConsoleEmailSender``); set ``SMTP_HOST`` to send via
real SMTP (``SMTPEmailSender`` — works with MailHog in dev or any provider's SMTP
in prod). Sending is best-effort: a delivery failure is logged, not raised, so it
never breaks the job that triggered it.
"""
from __future__ import annotations

import logging
import os
import smtplib
from abc import ABC, abstractmethod
from email.message import EmailMessage
from functools import lru_cache

logger = logging.getLogger("codebase_intelligence.email")


class EmailSender(ABC):
    @abstractmethod
    def send(self, to: str, subject: str, body: str) -> bool:
        """Return True if the message was handed off successfully."""


class ConsoleEmailSender(EmailSender):
    """No outbound connection — logs the message. The zero-config dev default."""

    def send(self, to: str, subject: str, body: str) -> bool:
        logger.info("[email:console] to=%s subject=%r\n%s", to, subject, body)
        return True


class SMTPEmailSender(EmailSender):
    def __init__(self, host: str, port: int, sender: str,
                 username: str | None = None, password: str | None = None,
                 use_tls: bool = False) -> None:
        self.host, self.port, self.sender = host, port, sender
        self.username, self.password, self.use_tls = username, password, use_tls

    def send(self, to: str, subject: str, body: str) -> bool:
        msg = EmailMessage()
        msg["From"] = self.sender
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        try:
            with smtplib.SMTP(self.host, self.port, timeout=10) as smtp:
                if self.use_tls:
                    smtp.starttls()
                if self.username:
                    smtp.login(self.username, self.password or "")
                smtp.send_message(msg)
            return True
        except Exception:  # best-effort: never break the caller
            logger.warning("failed to send email to %s", to, exc_info=True)
            return False


@lru_cache
def get_email_sender() -> EmailSender:
    host = os.getenv("SMTP_HOST")
    if not host:
        return ConsoleEmailSender()
    return SMTPEmailSender(
        host=host,
        port=int(os.getenv("SMTP_PORT", "25")),
        sender=os.getenv("SMTP_FROM", "noreply@codebase-intelligence.local"),
        username=os.getenv("SMTP_USERNAME") or None,
        password=os.getenv("SMTP_PASSWORD") or None,
        use_tls=os.getenv("SMTP_USE_TLS", "false").lower() == "true",
    )


def reset_email_sender_cache() -> None:
    get_email_sender.cache_clear()

"""Notifications: durable in-app store, pluggable email, and the job-event
dispatcher that fans out to both (Phase 3)."""
from .dispatch import notify_job_completion
from .email import EmailSender, get_email_sender, reset_email_sender_cache
from .store import (
    create_notification,
    list_for_user,
    mark_all_read,
    mark_read,
)

__all__ = [
    "notify_job_completion",
    "EmailSender",
    "get_email_sender",
    "reset_email_sender_cache",
    "create_notification",
    "list_for_user",
    "mark_all_read",
    "mark_read",
]

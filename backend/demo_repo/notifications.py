"""Outbound messages. ``send_sms`` is dead code on purpose."""
from models import LibraryItem, Member
from utils import cents_to_display


def send_receipt(member: Member, body: str) -> None:
    _deliver(member.email, "Your PyShelf receipt", body)


def send_overdue_notice(member: Member, item: LibraryItem, days_late: int,
                        fine_cents: int) -> None:
    body = (f"'{item.title}' came back {days_late} day(s) late. "
            f"A fine of {cents_to_display(fine_cents)} was added to your account.")
    _deliver(member.email, "Overdue item returned", body)


def send_sms(phone: str, body: str) -> None:
    """Never called from anywhere — the dead-code rule should flag this."""
    print(f"[sms -> {phone}] {body}")


def _deliver(address: str, subject: str, body: str) -> None:
    print(f"[mail -> {address}] {subject}\n{body}")

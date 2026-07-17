"""Loan lifecycle. ``process_return`` is a deliberately long method."""
from datetime import date, timedelta

from catalog import Catalog
from models import LibraryItem, Member
from notifications import send_overdue_notice, send_receipt
from utils import cents_to_display

LOAN_DAYS = 14
FINE_CENTS_PER_DAY = 25


class Loan:
    def __init__(self, item: LibraryItem, member: Member) -> None:
        self.item = item
        self.member = member
        self.borrowed_on = date.today()
        self.due_on = self.borrowed_on + timedelta(days=LOAN_DAYS)
        self.returned_on: date | None = None


class LoanService:
    def __init__(self, catalog: Catalog) -> None:
        self.catalog = catalog
        self.loans: list[Loan] = []

    def borrow(self, item_id: str, member_id: str) -> Loan | None:
        item = self.catalog.get_item(item_id)
        member = self.catalog.get_member(member_id)
        if item is None or member is None or not item.available:
            return None
        if member.owes_money():
            return None
        item.checkout()
        loan = Loan(item, member)
        self.loans.append(loan)
        return loan

    def process_return(self, item_id: str, member_id: str) -> str:
        """Handle a return end-to-end. Long on purpose (long-method smell)."""
        item = self.catalog.get_item(item_id)
        if item is None:
            return "unknown item"
        member = self.catalog.get_member(member_id)
        if member is None:
            return "unknown member"
        loan = None
        for candidate in self.loans:
            if candidate.item.id != item_id:
                continue
            if candidate.member.id != member_id:
                continue
            if candidate.returned_on is not None:
                continue
            loan = candidate
            break
        if loan is None:
            return "no open loan"
        today = date.today()
        loan.returned_on = today
        item.checkin()
        fine_cents = 0
        if today > loan.due_on:
            days_late = (today - loan.due_on).days
            fine_cents = days_late * FINE_CENTS_PER_DAY
            member.fines_cents += fine_cents
            send_overdue_notice(member, item, days_late, fine_cents)
        receipt_lines = [
            f"Returned: {item.title}",
            f"Borrowed: {loan.borrowed_on.isoformat()}",
            f"Due: {loan.due_on.isoformat()}",
            f"Returned on: {today.isoformat()}",
        ]
        if fine_cents:
            receipt_lines.append(f"Fine assessed: {cents_to_display(fine_cents)}")
        else:
            receipt_lines.append("Returned on time — no fine.")
        receipt = "\n".join(receipt_lines)
        send_receipt(member, receipt)
        return receipt

    def overdue_loans(self) -> list[Loan]:
        today = date.today()
        return [l for l in self.loans if l.returned_on is None and l.due_on < today]

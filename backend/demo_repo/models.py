"""Domain models for PyShelf."""
from dataclasses import dataclass, field
from datetime import date

from utils import make_id, slugify


class LibraryItem:
    """Base class for anything the library can lend out."""

    def __init__(self, title: str) -> None:
        self.id = make_id()
        self.title = title
        self.slug = slugify(title)
        self.available = True

    def checkout(self) -> None:
        self.available = False

    def checkin(self) -> None:
        self.available = True


class Book(LibraryItem):
    def __init__(self, title: str, author: str, isbn: str) -> None:
        super().__init__(title)
        self.author = author
        self.isbn = isbn

    def citation(self) -> str:
        return f"{self.author}. *{self.title}*. ISBN {self.isbn}."


class Magazine(LibraryItem):
    def __init__(self, title: str, issue: int) -> None:
        super().__init__(title)
        self.issue = issue

    def citation(self) -> str:
        return f"{self.title}, issue #{self.issue}."


class AudioBook(Book):
    """Books on tape — deepest point of the inheritance chain."""

    def __init__(self, title: str, author: str, isbn: str, minutes: int) -> None:
        super().__init__(title, author, isbn)
        self.minutes = minutes


@dataclass
class Member:
    name: str
    email: str
    id: str = field(default_factory=make_id)
    joined: date = field(default_factory=date.today)
    fines_cents: int = 0

    def owes_money(self) -> bool:
        return self.fines_cents > 0

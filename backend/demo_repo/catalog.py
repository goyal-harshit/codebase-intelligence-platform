"""The catalog — a deliberate god class for the risk detector to find."""
from models import AudioBook, Book, LibraryItem, Magazine, Member
from utils import clamp, slugify


class Catalog:
    """Owns every item, member, and lookup in the system.

    Doing far too much on purpose: item CRUD, member CRUD, search, stats,
    recommendations, and import/export all live here.
    """

    def __init__(self) -> None:
        self.items: dict[str, LibraryItem] = {}
        self.members: dict[str, Member] = {}

    # --- item management -------------------------------------------------
    def add_book(self, title: str, author: str, isbn: str) -> Book:
        book = Book(title, author, isbn)
        self.items[book.id] = book
        return book

    def add_magazine(self, title: str, issue: int) -> Magazine:
        mag = Magazine(title, issue)
        self.items[mag.id] = mag
        return mag

    def add_audiobook(self, title: str, author: str, isbn: str, minutes: int) -> AudioBook:
        audio = AudioBook(title, author, isbn, minutes)
        self.items[audio.id] = audio
        return audio

    def remove_item(self, item_id: str) -> bool:
        return self.items.pop(item_id, None) is not None

    def get_item(self, item_id: str) -> LibraryItem | None:
        return self.items.get(item_id)

    # --- member management ------------------------------------------------
    def register_member(self, name: str, email: str) -> Member:
        member = Member(name, email)
        self.members[member.id] = member
        return member

    def remove_member(self, member_id: str) -> bool:
        return self.members.pop(member_id, None) is not None

    def get_member(self, member_id: str) -> Member | None:
        return self.members.get(member_id)

    # --- search & stats -----------------------------------------------------
    def search(self, query: str) -> list[LibraryItem]:
        needle = slugify(query)
        return [i for i in self.items.values() if needle in i.slug]

    def available_items(self) -> list[LibraryItem]:
        return [i for i in self.items.values() if i.available]

    def count_items(self) -> int:
        return len(self.items)

    def count_members(self) -> int:
        return len(self.members)

    def members_with_fines(self) -> list[Member]:
        return [m for m in self.members.values() if m.owes_money()]

    # --- recommendations -----------------------------------------------------
    def recommend(self, member: Member, limit: int = 3) -> list[LibraryItem]:
        limit = clamp(limit, 1, 10)
        return self.available_items()[:limit]

    # --- import/export --------------------------------------------------------
    def export_titles(self) -> list[str]:
        return sorted(i.title for i in self.items.values())

    def import_books(self, rows: list[tuple[str, str, str]]) -> int:
        for title, author, isbn in rows:
            self.add_book(title, author, isbn)
        return len(rows)

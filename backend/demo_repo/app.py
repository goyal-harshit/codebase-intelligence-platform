"""PyShelf entry point — wires the catalog and loan service together."""
from catalog import Catalog
from loans import LoanService


def seed_catalog(catalog: Catalog) -> None:
    catalog.add_book("The Pragmatic Programmer", "Hunt & Thomas", "978-0201616224")
    catalog.add_book("A City Made of Words", "Paul Park", "978-1629632429")
    catalog.add_magazine("Systems Quarterly", 42)
    catalog.add_audiobook("Working in Public", "Nadia Eghbal", "978-0578675862", 415)
    catalog.register_member("Ada Lovelace", "ada@example.com")
    catalog.register_member("Grace Hopper", "grace@example.com")


def main() -> None:
    catalog = Catalog()
    loans = LoanService(catalog)
    seed_catalog(catalog)

    member = next(iter(catalog.members.values()))
    item = catalog.available_items()[0]
    loan = loans.borrow(item.id, member.id)
    if loan is not None:
        print(loans.process_return(item.id, member.id))
    print(f"{catalog.count_items()} items, {catalog.count_members()} members")
    for pick in catalog.recommend(member):
        print(f"try next: {pick.title}")


if __name__ == "__main__":
    main()

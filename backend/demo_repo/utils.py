"""Shared helpers — deliberately called from every module (shotgun surgery)."""
import re
import uuid


def make_id() -> str:
    return uuid.uuid4().hex[:10]


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def cents_to_display(cents: int) -> str:
    return f"${cents / 100:.2f}"


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))

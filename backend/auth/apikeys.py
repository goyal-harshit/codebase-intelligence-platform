"""Per-user API keys: generation, hashing, verification, lifecycle.

Phase 2 (FULL_STACK_GAP_PLAN.md §5) makes API-key auth *per-user*: a logged-in
user issues keys from a settings page and revokes them later, while the static
service ``API_KEY`` env value stays as a separate service-to-service credential.

Only a SHA-256 hash of each key is stored (``api_keys.key_hash``); the raw secret
is returned exactly once at creation time and is otherwise unrecoverable.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional

import db as _db
from db import ApiKey

# Recognisable prefix so a leaked secret is easy to grep/scan for, and so users
# can tell our keys apart from other tokens in their secret stores.
KEY_PREFIX = "cik_"


def generate_key() -> str:
    return KEY_PREFIX + secrets.token_urlsafe(32)


def hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def create_api_key(user_id: str, name: Optional[str] = None) -> tuple[str, dict]:
    """Issue a new key for ``user_id``. Returns ``(raw_key, metadata)``.

    The raw key is shown to the caller once and never stored in plaintext.
    """
    raw = generate_key()
    with _db.get_sessionmaker()() as s:
        row = ApiKey(user_id=user_id, key_hash=hash_key(raw), name=name)
        s.add(row)
        s.commit()
        meta = _to_dict(row)
    return raw, meta


def list_api_keys(user_id: str) -> list[dict]:
    with _db.get_sessionmaker()() as s:
        rows = (
            s.query(ApiKey)
            .filter(ApiKey.user_id == user_id)
            .order_by(ApiKey.created_at.desc())
            .all()
        )
        return [_to_dict(r) for r in rows]


def revoke_api_key(user_id: str, key_id: str) -> bool:
    """Mark a key revoked. Scoped to ``user_id`` so users can't revoke others'
    keys. Returns True if a matching, non-revoked key was found."""
    with _db.get_sessionmaker()() as s:
        row = s.get(ApiKey, key_id)
        if row is None or row.user_id != user_id:
            return False
        if row.revoked:
            return False
        row.revoked = True
        s.commit()
        return True


def verify_api_key(raw: str) -> Optional[str]:
    """Return the owning ``user_id`` for a valid, non-revoked key, else None.

    Constant work regardless of match: we always hash, then look up by hash
    (the column is indexed and the hash space makes the lookup effectively a
    digest comparison, so there is no user-enumeration timing signal).
    """
    if not raw:
        return None
    h = hash_key(raw)
    with _db.get_sessionmaker()() as s:
        row = (
            s.query(ApiKey)
            .filter(ApiKey.key_hash == h, ApiKey.revoked.is_(False))
            .first()
        )
        if row is None:
            return None
        row.last_used_at = datetime.now(timezone.utc)
        user_id = row.user_id
        s.commit()
        return user_id


def _to_dict(row: ApiKey) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "revoked": row.revoked,
        "created_at": row.created_at,
        "last_used_at": row.last_used_at,
    }

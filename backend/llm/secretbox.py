"""Symmetric encryption for secrets stored at rest (plan Phase C).

The LLM provider API key must be *recoverable* (we send it to the provider), so
unlike ``auth/apikeys.py`` — which one-way hashes — this uses Fernet symmetric
encryption. The key is derived from ``LLM_CONFIG_SECRET`` (falling back to the
existing ``AUTH_SECRET``) so no new secret has to be provisioned for dev.

If ``cryptography`` is unavailable the functions raise a clear error rather than
storing plaintext.
"""
from __future__ import annotations

import base64
import hashlib
import os


def _fernet():
    from cryptography.fernet import Fernet  # imported lazily; clear error if missing

    secret = (
        os.getenv("LLM_CONFIG_SECRET")
        or os.getenv("AUTH_SECRET")
        or "dev-insecure-change-me"
    )
    # Fernet needs a 32-byte urlsafe-base64 key; derive one deterministically.
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
    return Fernet(key)


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt(token: str) -> str:
    return _fernet().decrypt(token.encode("ascii")).decode("utf-8")

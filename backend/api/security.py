"""Request authentication for data routes.

Phase 1 shipped a single static service key. Phase 2 (FULL_STACK_GAP_PLAN.md §5)
generalises this into a *principal*: a data route is authorised when the caller
presents ONE of three credentials, resolved in priority order:

  1. a valid JWT (a logged-in user)             -> Principal(kind="user")
  2. the static service ``API_KEY`` in X-API-Key -> Principal(kind="service")
  3. a valid per-user API key in X-API-Key       -> Principal(kind="user")

Enforcement stays opt-in via the ``API_KEY`` env var, preserving the Phase 1
contract and the offline test suite:

* ``API_KEY`` set   -> a request with no valid credential gets 401.
* ``API_KEY`` unset -> auth is disabled (dev mode); an anonymous principal is
  returned and ``main`` logs a one-time startup warning.

``API_KEY`` is read from the environment on each call (not cached) so tests can
flip it per-case, matching how the service clients in this package read env.
"""
from __future__ import annotations

import hmac
import os
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, Request, status

API_KEY_HEADER = "X-API-Key"


@dataclass
class Principal:
    """Who is calling, and how. ``user_id`` is None for the service key and for
    anonymous dev-mode access."""

    user_id: str | None
    kind: str  # "user" | "service" | "anon"
    is_superuser: bool = False


def require_api_key(
    x_api_key: str | None = Header(default=None, alias=API_KEY_HEADER),
) -> None:
    """Legacy service-only gate (static key). Retained for service-to-service
    callers and tooling; data routes use ``get_principal`` below."""
    configured = os.getenv("API_KEY") or None
    if not configured:
        return  # auth disabled (dev mode)
    if not x_api_key or not hmac.compare_digest(x_api_key, configured):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing or invalid API key",
            headers={"WWW-Authenticate": API_KEY_HEADER},
        )


from auth.users import fastapi_users

# A logged-in user if a valid JWT is present, else None (does not 401 on its own).
_optional_current_user = fastapi_users.current_user(active=True, optional=True)


async def get_principal(
    request: Request,
    user=Depends(_optional_current_user),
    x_api_key: str | None = Header(default=None, alias=API_KEY_HEADER),
) -> Principal:
    service_key = os.getenv("API_KEY") or None

    # 1. logged-in user (JWT bearer)
    if user is not None:
        return Principal(user_id=user.id, kind="user", is_superuser=bool(user.is_superuser))

    # 2. static service key (constant-time compare)
    if x_api_key and service_key and hmac.compare_digest(x_api_key, service_key):
        return Principal(user_id=None, kind="service", is_superuser=True)

    # 3. per-user API key (DB-backed, hashed lookup)
    if x_api_key:
        from auth.apikeys import verify_api_key

        owner = verify_api_key(x_api_key)
        if owner:
            return Principal(user_id=owner, kind="user")

    # 4. nothing valid presented
    if service_key is None:
        return Principal(user_id=None, kind="anon")  # dev open mode

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="authentication required (JWT bearer or X-API-Key)",
        headers={"WWW-Authenticate": "Bearer"},
    )

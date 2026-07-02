"""GitHub OAuth sign-in (the "step 5" the user model already carries fields for).

Flow: ``GET /auth/github/login`` redirects to GitHub's authorize page with a
signed short-lived state token; GitHub redirects back to
``GET /auth/github/callback``, which exchanges the code for an access token,
fetches the user's identity/primary email, finds-or-creates the local account
(``oauth_provider``/``oauth_subject`` on ``User``), then hands the SPA a
regular FastAPI-Users JWT in the URL fragment of the frontend login page
(fragments never reach server logs, unlike query strings).

Enabled only when ``GITHUB_CLIENT_ID``/``GITHUB_CLIENT_SECRET`` are set (a
free OAuth App from github.com/settings/developers). ``GET /auth/providers``
lets the UI discover whether to show the button. No paid services involved.
"""
from __future__ import annotations

import os
import secrets
from urllib.parse import urlencode

import httpx
import jwt as pyjwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi_users.jwt import decode_jwt, generate_jwt
from fastapi_users.password import PasswordHelper
from sqlalchemy import select

from db import User, get_async_session

from .users import AUTH_SECRET, get_jwt_strategy

router = APIRouter()

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_URL = "https://api.github.com"
STATE_AUDIENCE = "codeintel:oauth-state"
STATE_LIFETIME_SECONDS = 600


def _client_id() -> str:
    return os.getenv("GITHUB_CLIENT_ID", "")


def _client_secret() -> str:
    return os.getenv("GITHUB_CLIENT_SECRET", "")


def _frontend_url() -> str:
    return os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")


def _redirect_uri() -> str:
    # Where GitHub sends the user back; must match the OAuth App's setting.
    explicit = os.getenv("GITHUB_OAUTH_REDIRECT_URL")
    if explicit:
        return explicit
    base = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
    return f"{base}/auth/github/callback"


def _require_configured() -> None:
    if not (_client_id() and _client_secret()):
        raise HTTPException(
            status_code=503,
            detail="GitHub OAuth is not configured (set GITHUB_CLIENT_ID / GITHUB_CLIENT_SECRET).",
        )


async def _fetch_github_token(code: str) -> str:
    """Exchange the authorization code for a GitHub access token."""
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": _client_id(),
                "client_secret": _client_secret(),
                "code": code,
                "redirect_uri": _redirect_uri(),
            },
        )
    token = r.json().get("access_token") if r.status_code == 200 else None
    if not token:
        raise HTTPException(status_code=400, detail="GitHub code exchange failed.")
    return token


async def _fetch_github_profile(access_token: str) -> dict:
    """Return {id, email, name} for the GitHub user, resolving a hidden email
    via the /user/emails endpoint (primary + verified wins)."""
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"}
    async with httpx.AsyncClient(timeout=15) as client:
        user_resp = await client.get(f"{GITHUB_API_URL}/user", headers=headers)
        if user_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Could not fetch GitHub profile.")
        profile = user_resp.json()
        email = profile.get("email")
        if not email:
            emails_resp = await client.get(f"{GITHUB_API_URL}/user/emails", headers=headers)
            if emails_resp.status_code == 200:
                candidates = emails_resp.json()
                primary = [e for e in candidates if e.get("primary") and e.get("verified")]
                verified = [e for e in candidates if e.get("verified")]
                chosen = (primary or verified or [{}])[0]
                email = chosen.get("email")
    if not email:
        raise HTTPException(
            status_code=400,
            detail="GitHub account has no verified email; add one on GitHub and retry.",
        )
    return {"id": str(profile["id"]), "email": email, "name": profile.get("name")}


@router.get("/providers")
async def list_providers() -> dict:
    """Which OAuth providers are configured — the SPA uses this to decide
    whether to render the 'Continue with GitHub' button."""
    return {"github": bool(_client_id() and _client_secret())}


@router.get("/github/login")
async def github_login() -> RedirectResponse:
    _require_configured()
    state = generate_jwt(
        {"aud": STATE_AUDIENCE, "nonce": secrets.token_urlsafe(16)},
        AUTH_SECRET,
        STATE_LIFETIME_SECONDS,
    )
    params = urlencode(
        {
            "client_id": _client_id(),
            "redirect_uri": _redirect_uri(),
            "scope": "read:user user:email",
            "state": state,
        }
    )
    return RedirectResponse(f"{GITHUB_AUTHORIZE_URL}?{params}", status_code=302)


@router.get("/github/callback")
async def github_callback(
    code: str,
    state: str,
    session=Depends(get_async_session),
) -> RedirectResponse:
    _require_configured()
    try:
        decode_jwt(state, AUTH_SECRET, [STATE_AUDIENCE])
    except pyjwt.PyJWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state.")

    access_token = await _fetch_github_token(code)
    profile = await _fetch_github_profile(access_token)

    # Match by GitHub identity first, then link by email (an existing
    # password account signing in with GitHub for the first time).
    result = await session.execute(
        select(User).where(
            User.oauth_provider == "github", User.oauth_subject == profile["id"]
        )
    )
    user = result.scalar_one_or_none()
    if user is None:
        result = await session.execute(select(User).where(User.email == profile["email"]))
        user = result.scalar_one_or_none()
        if user is not None:
            user.oauth_provider = "github"
            user.oauth_subject = profile["id"]
        else:
            user = User(
                email=profile["email"],
                # OAuth accounts have no usable password; store a random hash
                # so the column stays non-null and password login always fails.
                hashed_password=PasswordHelper().hash(secrets.token_urlsafe(32)),
                full_name=profile.get("name"),
                oauth_provider="github",
                oauth_subject=profile["id"],
                is_active=True,
                is_verified=True,
            )
            session.add(user)
        await session.commit()
        await session.refresh(user)

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled.")

    jwt_token = await get_jwt_strategy().write_token(user)
    return RedirectResponse(f"{_frontend_url()}/login#token={jwt_token}", status_code=302)

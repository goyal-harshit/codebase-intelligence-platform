"""GitHub OAuth flow (offline: GitHub's API is monkeypatched)."""
import pytest

pytest.importorskip("fastapi_users")
from fastapi.testclient import TestClient  # noqa: E402
from fastapi_users.jwt import generate_jwt  # noqa: E402

from auth import oauth_github  # noqa: E402
from auth.users import AUTH_SECRET  # noqa: E402
from main import app  # noqa: E402

client = TestClient(app)

GH_PROFILE = {"id": "12345", "email": "octo@example.com", "name": "Octo Cat"}


def _configure(monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "test-client-secret")


def _valid_state():
    return generate_jwt(
        {"aud": oauth_github.STATE_AUDIENCE, "nonce": "n"}, AUTH_SECRET, 600
    )


def _mock_github(monkeypatch, profile=GH_PROFILE):
    async def fake_token(code):
        assert code == "good-code"
        return "gh-access-token"

    async def fake_profile(access_token):
        assert access_token == "gh-access-token"
        return dict(profile)

    monkeypatch.setattr(oauth_github, "_fetch_github_token", fake_token)
    monkeypatch.setattr(oauth_github, "_fetch_github_profile", fake_profile)


def test_providers_reflects_config(monkeypatch):
    monkeypatch.delenv("GITHUB_CLIENT_ID", raising=False)
    monkeypatch.delenv("GITHUB_CLIENT_SECRET", raising=False)
    assert client.get("/auth/providers").json() == {"github": False}
    _configure(monkeypatch)
    assert client.get("/auth/providers").json() == {"github": True}


def test_login_unconfigured_returns_503(monkeypatch):
    monkeypatch.delenv("GITHUB_CLIENT_ID", raising=False)
    monkeypatch.delenv("GITHUB_CLIENT_SECRET", raising=False)
    assert client.get("/auth/github/login", follow_redirects=False).status_code == 503


def test_login_redirects_to_github_with_state(monkeypatch):
    _configure(monkeypatch)
    r = client.get("/auth/github/login", follow_redirects=False)
    assert r.status_code == 302
    loc = r.headers["location"]
    assert loc.startswith(oauth_github.GITHUB_AUTHORIZE_URL)
    assert "client_id=test-client-id" in loc
    assert "state=" in loc


def test_callback_rejects_bad_state(monkeypatch):
    _configure(monkeypatch)
    r = client.get(
        "/auth/github/callback",
        params={"code": "good-code", "state": "forged"},
        follow_redirects=False,
    )
    assert r.status_code == 400


def test_callback_creates_user_and_hands_token_to_spa(monkeypatch):
    _configure(monkeypatch)
    _mock_github(monkeypatch)
    r = client.get(
        "/auth/github/callback",
        params={"code": "good-code", "state": _valid_state()},
        follow_redirects=False,
    )
    assert r.status_code == 302, r.text
    loc = r.headers["location"]
    assert "/login#token=" in loc
    token = loc.split("#token=", 1)[1]

    me = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200, me.text
    assert me.json()["email"] == GH_PROFILE["email"]

    # Second sign-in reuses the account (matched on oauth_subject).
    r2 = client.get(
        "/auth/github/callback",
        params={"code": "good-code", "state": _valid_state()},
        follow_redirects=False,
    )
    token2 = r2.headers["location"].split("#token=", 1)[1]
    me2 = client.get("/users/me", headers={"Authorization": f"Bearer {token2}"})
    assert me2.json()["id"] == me.json()["id"]


def test_callback_links_existing_password_account(monkeypatch):
    _configure(monkeypatch)
    cred = {"email": "linked@example.com", "password": "s3cret-pw"}
    reg = client.post("/auth/register", json=cred)
    assert reg.status_code in (200, 201), reg.text

    _mock_github(monkeypatch, {"id": "777", "email": cred["email"], "name": None})
    r = client.get(
        "/auth/github/callback",
        params={"code": "good-code", "state": _valid_state()},
        follow_redirects=False,
    )
    assert r.status_code == 302, r.text
    token = r.headers["location"].split("#token=", 1)[1]
    me = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    # Linked, not duplicated: same account id as the password registration.
    assert me.json()["id"] == reg.json()["id"]

    # Password login still works after linking.
    login = client.post(
        "/auth/jwt/login",
        data={"username": cred["email"], "password": cred["password"]},
    )
    assert login.status_code == 200

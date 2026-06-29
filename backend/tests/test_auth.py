"""FastAPI-Users email/password + JWT auth flow (offline, SQLite)."""
import pytest

pytest.importorskip("fastapi_users")
from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

client = TestClient(app)

CRED = {"email": "alice@example.com", "password": "s3cret-pw"}


def test_register_then_login_then_me():
    # Register
    r = client.post("/auth/register", json=CRED)
    assert r.status_code in (200, 201), r.text
    body = r.json()
    assert body["email"] == CRED["email"]
    assert "id" in body and "hashed_password" not in body

    # Login (OAuth2 password form: username + password)
    r = client.post("/auth/jwt/login",
                    data={"username": CRED["email"], "password": CRED["password"]})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    assert token

    # Authenticated /users/me
    r = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == CRED["email"]


def test_me_requires_auth():
    assert client.get("/users/me").status_code == 401


def test_login_wrong_password_rejected():
    client.post("/auth/register", json={"email": "bob@example.com", "password": "rightpw1"})
    r = client.post("/auth/jwt/login",
                    data={"username": "bob@example.com", "password": "wrongpw"})
    assert r.status_code == 400


def test_auth_routes_are_open_not_api_key_gated(monkeypatch):
    # Even with API_KEY set, the auth router must remain reachable (it is not
    # behind the data-route API-key dependency).
    monkeypatch.setenv("API_KEY", "secret")
    r = client.post("/auth/jwt/login",
                    data={"username": "nobody@example.com", "password": "x"})
    assert r.status_code in (400, 401)  # reachable -> bad creds, not 401-from-api-key-gate

"""Per-user API keys: issuance, listing, revocation, and use as a data-route
credential alongside JWT and the static service key (Phase 2)."""
import pytest

pytest.importorskip("fastapi_users")
from fastapi.testclient import TestClient  # noqa: E402

from auth.apikeys import KEY_PREFIX, hash_key, verify_api_key  # noqa: E402
from main import app  # noqa: E402

client = TestClient(app)

CRED = {"email": "keys-user@example.com", "password": "s3cret-pw"}


def _token() -> str:
    client.post("/auth/register", json=CRED)
    r = client.post(
        "/auth/jwt/login",
        data={"username": CRED["email"], "password": CRED["password"]},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_create_lists_and_revokes_key():
    auth = {"Authorization": f"Bearer {_token()}"}

    # Create: raw key returned exactly once, with the recognisable prefix.
    r = client.post("/api/v1/keys", json={"name": "ci"}, headers=auth)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["key"].startswith(KEY_PREFIX)
    assert body["name"] == "ci" and body["revoked"] is False
    key_id, raw = body["id"], body["key"]

    # List: metadata only, never the raw secret.
    r = client.get("/api/v1/keys", headers=auth)
    assert r.status_code == 200
    listed = r.json()
    assert any(k["id"] == key_id for k in listed)
    assert all("key" not in k for k in listed)

    # The stored hash matches the raw key; the raw key resolves to the owner.
    assert verify_api_key(raw) is not None

    # Revoke: idempotency — second delete is a 404.
    assert client.delete(f"/api/v1/keys/{key_id}", headers=auth).status_code == 204
    assert client.delete(f"/api/v1/keys/{key_id}", headers=auth).status_code == 404
    # Revoked key no longer verifies.
    assert verify_api_key(raw) is None


def test_key_routes_require_login():
    assert client.get("/api/v1/keys").status_code == 401
    assert client.post("/api/v1/keys", json={}).status_code == 401


def test_per_user_key_authenticates_data_route(monkeypatch):
    # With enforcement ON, a freshly issued per-user key clears the data-route
    # gate (degrading to 503/200 from the missing graph backend, never 401).
    auth = {"Authorization": f"Bearer {_token()}"}
    raw = client.post("/api/v1/keys", json={}, headers=auth).json()["key"]

    monkeypatch.setenv("API_KEY", "service-secret")
    r = client.get("/api/v1/stats", headers={"X-API-Key": raw})
    assert r.status_code in (200, 503)

    # A bogus key is still rejected.
    assert client.get("/api/v1/stats", headers={"X-API-Key": "cik_nope"}).status_code == 401


def test_hash_is_not_reversible_and_deterministic():
    assert hash_key("abc") == hash_key("abc")
    assert hash_key("abc") != "abc"
    assert len(hash_key("abc")) == 64  # sha256 hex

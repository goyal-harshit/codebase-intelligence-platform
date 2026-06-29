"""Per-repo RBAC: role ordering, membership grants, and route enforcement
(Phase 2, FULL_STACK_GAP_PLAN.md §5)."""
import pytest

pytest.importorskip("fastapi_users")
from fastapi.testclient import TestClient  # noqa: E402

from auth.rbac import role_satisfies  # noqa: E402
from db import ROLE_MEMBER, ROLE_OWNER, ROLE_VIEWER  # noqa: E402
from main import app  # noqa: E402

client = TestClient(app)


def _user_token(email: str) -> tuple[str, str]:
    """Register/login a user; returns (bearer_token, user_id)."""
    cred = {"email": email, "password": "s3cret-pw"}
    client.post("/auth/register", json=cred)
    r = client.post("/auth/jwt/login", data={"username": email, "password": cred["password"]})
    token = r.json()["access_token"]
    me = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    return token, me.json()["id"]


def test_role_ordering():
    assert role_satisfies(ROLE_OWNER, ROLE_VIEWER)
    assert role_satisfies(ROLE_MEMBER, ROLE_MEMBER)
    assert not role_satisfies(ROLE_VIEWER, ROLE_MEMBER)
    assert not role_satisfies(None, ROLE_VIEWER)


def test_creator_is_owner_and_can_manage_members():
    owner_tok, _ = _user_token("rbac-owner@example.com")
    _, member_id = _user_token("rbac-member@example.com")
    oh = {"Authorization": f"Bearer {owner_tok}"}

    # Create repo -> creator is owner.
    r = client.post("/api/v1/repos", json={"name": "demo"}, headers=oh)
    assert r.status_code == 201, r.text
    repo = r.json()
    assert repo["role"] == ROLE_OWNER
    repo_id = repo["id"]

    # It shows up in the owner's repo list.
    mine = client.get("/api/v1/repos", headers=oh).json()
    assert any(x["id"] == repo_id for x in mine)

    # Owner grants a member.
    r = client.put(
        f"/api/v1/repos/{repo_id}/members",
        json={"user_id": member_id, "role": ROLE_MEMBER},
        headers=oh,
    )
    assert r.status_code == 200, r.text
    members = {m["user_id"]: m["role"] for m in r.json()}
    assert members[member_id] == ROLE_MEMBER

    # Unknown user -> 404.
    assert client.put(
        f"/api/v1/repos/{repo_id}/members",
        json={"user_id": "deadbeef", "role": ROLE_MEMBER},
        headers=oh,
    ).status_code == 404


def test_non_member_is_forbidden_and_member_cannot_grant():
    owner_tok, _ = _user_token("rbac-o2@example.com")
    member_tok, member_id = _user_token("rbac-m2@example.com")
    stranger_tok, _ = _user_token("rbac-stranger@example.com")
    oh = {"Authorization": f"Bearer {owner_tok}"}

    repo_id = client.post("/api/v1/repos", json={"name": "x"}, headers=oh).json()["id"]
    client.put(
        f"/api/v1/repos/{repo_id}/members",
        json={"user_id": member_id, "role": ROLE_MEMBER},
        headers=oh,
    )

    # Stranger (no membership) cannot even list members.
    sh = {"Authorization": f"Bearer {stranger_tok}"}
    assert client.get(f"/api/v1/repos/{repo_id}/members", headers=sh).status_code == 403

    # A member (viewer+) can list, but cannot grant (owner-only).
    mh = {"Authorization": f"Bearer {member_tok}"}
    assert client.get(f"/api/v1/repos/{repo_id}/members", headers=mh).status_code == 200
    assert client.put(
        f"/api/v1/repos/{repo_id}/members",
        json={"user_id": member_id, "role": ROLE_OWNER},
        headers=mh,
    ).status_code == 403


def test_repo_routes_require_login():
    assert client.get("/api/v1/repos").status_code == 401
    assert client.post("/api/v1/repos", json={"name": "x"}).status_code == 401

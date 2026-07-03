"""Notifications (Phase 3): durable store, pluggable email, dispatcher, REST,
WebSocket streaming, and the end-to-end job-completion path."""
import pytest

pytest.importorskip("fastapi_users")
from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402
from notifications import (  # noqa: E402
    create_notification,
    list_for_user,
    mark_all_read,
    mark_read,
)
from notifications import dispatch as _dispatch  # noqa: E402
from notifications.email import (  # noqa: E402
    ConsoleEmailSender,
    SMTPEmailSender,
    get_email_sender,
    reset_email_sender_cache,
)

client = TestClient(app)


def _user(email: str) -> tuple[str, str]:
    cred = {"email": email, "password": "s3cret-pw"}
    client.post("/auth/register", json=cred)
    tok = client.post(
        "/auth/jwt/login", data={"username": email, "password": cred["password"]}
    ).json()["access_token"]
    uid = client.get("/users/me", headers={"Authorization": f"Bearer {tok}"}).json()["id"]
    return tok, uid


# -- store ----------------------------------------------------------------

def test_store_create_list_and_mark_read():
    _, uid = _user("notif-store@example.com")
    create_notification(uid, "first", level="info")
    n = create_notification(uid, "second", level="success", body="done")
    rows = list_for_user(uid)
    assert {r["title"] for r in rows} >= {"first", "second"}

    assert mark_read(uid, n["id"]) is True
    assert mark_read(uid, n["id"]) is False  # already read
    assert mark_read("someone-else", n["id"]) is False  # not your notification

    unread = list_for_user(uid, unread_only=True)
    assert all(r["id"] != n["id"] for r in unread)


def test_mark_all_read():
    _, uid = _user("notif-since@example.com")
    create_notification(uid, "new-one")
    assert mark_all_read(uid) >= 1
    assert list_for_user(uid, unread_only=True) == []


# -- email ----------------------------------------------------------------

def test_email_sender_defaults_to_console(monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    reset_email_sender_cache()
    try:
        assert isinstance(get_email_sender(), ConsoleEmailSender)
    finally:
        reset_email_sender_cache()


def test_email_sender_uses_smtp_when_configured(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "localhost")
    reset_email_sender_cache()
    try:
        assert isinstance(get_email_sender(), SMTPEmailSender)
    finally:
        reset_email_sender_cache()


def test_console_sender_send_returns_true():
    assert ConsoleEmailSender().send("a@b.c", "subj", "body") is True


# -- dispatcher -----------------------------------------------------------

def test_dispatch_writes_notification_and_emails(monkeypatch):
    _, uid = _user("notif-dispatch@example.com")
    sent = []

    class Recorder:
        def send(self, to, subject, body):
            sent.append((to, subject))
            return True

    monkeypatch.setattr(_dispatch, "get_email_sender", lambda: Recorder())
    _dispatch.notify_job_completion(
        "job-123", uid, "complete", result={"files": 3, "entities": 9, "risks": 1}
    )
    titles = [r["title"] for r in list_for_user(uid)]
    assert "Ingestion complete" in titles
    assert sent and sent[0][0] == "notif-dispatch@example.com"


def test_dispatch_anonymous_job_skips_email(monkeypatch):
    sent = []
    monkeypatch.setattr(_dispatch, "get_email_sender",
                        lambda: type("R", (), {"send": lambda self, *a: sent.append(a)})())
    _dispatch.notify_job_completion("job-x", None, "failed", error="boom")
    assert sent == []  # no user -> no email


# -- REST -----------------------------------------------------------------

def test_rest_list_and_mark_read():
    tok, uid = _user("notif-rest@example.com")
    create_notification(uid, "hello")
    h = {"Authorization": f"Bearer {tok}"}
    rows = client.get("/api/v1/notifications", headers=h).json()
    assert any(r["title"] == "hello" for r in rows)
    nid = rows[0]["id"]
    assert client.post(f"/api/v1/notifications/{nid}/read", headers=h).status_code == 200
    assert client.post("/api/v1/notifications/read-all", headers=h).status_code == 200


def test_rest_requires_login():
    assert client.get("/api/v1/notifications").status_code == 401


# -- WebSocket ------------------------------------------------------------

def test_ws_rejects_bad_token():
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/notifications?token=bogus"):
            pass


def test_ws_streams_new_notification(monkeypatch):
    monkeypatch.setenv("WS_POLL_INTERVAL", "0.1")
    tok, uid = _user("notif-ws@example.com")
    with client.websocket_connect(f"/ws/notifications?token={tok}") as ws:
        create_notification(uid, "live-event", level="success")
        data = ws.receive_json()
        assert data["title"] == "live-event"
        assert data["level"] == "success"


# -- end-to-end job completion -------------------------------------------

def test_ingest_failure_notifies_owner(monkeypatch):
    # Logged-in user starts an ingest; with no graph backend the task fails
    # and dispatches a failure notification attributed to that user. The task
    # runs in a background thread (non-blocking dispatch), so poll briefly.
    import time

    monkeypatch.delenv("API_KEY", raising=False)
    tok, uid = _user("notif-e2e@example.com")
    h = {"Authorization": f"Bearer {tok}"}
    r = client.post("/api/v1/ingest", json={"repo_path": "/no/such/repo"}, headers=h)
    assert r.status_code == 200, r.text
    deadline = time.monotonic() + 10
    titles: list[str] = []
    while time.monotonic() < deadline:
        titles = [n["title"] for n in list_for_user(uid)]
        if any("Ingestion" in t for t in titles):
            break
        time.sleep(0.2)
    assert any("Ingestion" in t for t in titles)

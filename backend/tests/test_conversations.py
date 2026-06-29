"""Multi-turn conversation history: store + multi-turn query wiring (Phase 4)."""
import pytest

import conversations as conv

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from api.deps import get_query_engine  # noqa: E402
from main import app  # noqa: E402


# -- store ----------------------------------------------------------------

def test_store_roundtrip_and_history_formatting():
    c = conv.create_conversation(None, title="t")
    conv.add_message(c["id"], "user", "what is foo?")
    conv.add_message(c["id"], "assistant", "foo is a function")
    msgs = conv.get_messages(c["id"])
    assert [m["role"] for m in msgs] == ["user", "assistant"]

    block = conv.format_history(conv.recent_messages(c["id"]))
    assert "User: what is foo?" in block
    assert "Assistant: foo is a function" in block


def test_format_history_empty():
    assert conv.format_history([]) == ""


def test_recent_messages_bounded():
    c = conv.create_conversation(None)
    for i in range(15):
        conv.add_message(c["id"], "user", f"m{i}")
    recent = conv.recent_messages(c["id"], turns=5)
    assert len(recent) == 5
    assert recent[-1]["content"] == "m14"  # newest kept, oldest-first order


# -- multi-turn query wiring ---------------------------------------------

class _FakeEngine:
    def answer(self, question, top_k=10, history=""):
        return {"question": question, "strategy": "semantic",
                "answer": f"A:{question}", "sources": [], "cypher": None,
                "history_seen": history}


@pytest.fixture
def client_with_fake_engine(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    app.dependency_overrides[get_query_engine] = lambda: _FakeEngine()
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_query_engine, None)


def test_query_persists_and_feeds_back_history(client_with_fake_engine):
    client = client_with_fake_engine
    sid = client.post("/api/v1/conversations", json={"title": "s"}).json()["id"]

    r1 = client.get("/api/v1/query", params={"q": "first?", "session_id": sid})
    assert r1.status_code == 200, r1.text
    assert r1.json()["history_seen"] == ""  # turn one: no prior context

    r2 = client.get("/api/v1/query", params={"q": "second?", "session_id": sid})
    seen = r2.json()["history_seen"]
    assert "first?" in seen and "A:first?" in seen  # prior turn fed back

    msgs = client.get(f"/api/v1/conversations/{sid}/messages").json()
    assert [m["content"] for m in msgs] == ["first?", "A:first?", "second?", "A:second?"]


def test_query_without_session_has_no_history(client_with_fake_engine):
    r = client_with_fake_engine.get("/api/v1/query", params={"q": "hi"})
    assert r.status_code == 200
    assert r.json()["history_seen"] == ""

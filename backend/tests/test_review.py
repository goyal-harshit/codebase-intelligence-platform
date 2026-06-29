"""AI code review core + endpoint (Phase 4 item 5)."""
import pytest

from api import review

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from api.deps import get_llm  # noqa: E402
from main import app  # noqa: E402


class _FakeLLM:
    def __init__(self):
        self.last_prompt = None

    def generate(self, prompt, temperature=0.2):
        self.last_prompt = prompt
        return "REVIEW"


def test_review_diff_renders_prompt():
    llm = _FakeLLM()
    out = review.review_diff(llm, "--- a/x.py\n+++ b/x.py\n+print('hi')")
    assert out == "REVIEW"
    assert "print('hi')" in llm.last_prompt


def test_review_caps_diff():
    llm = _FakeLLM()
    review.review_diff(llm, "x" * 50000)
    assert len(llm.last_prompt) < 50000


@pytest.fixture
def client_with_fake_llm(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    app.dependency_overrides[get_llm] = lambda: _FakeLLM()
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_llm, None)


def test_review_endpoint(client_with_fake_llm):
    r = client_with_fake_llm.post("/api/v1/review", json={"diff": "+ added line"})
    assert r.status_code == 200, r.text
    assert r.json()["review"] == "REVIEW"


def test_review_endpoint_rejects_empty(client_with_fake_llm):
    assert client_with_fake_llm.post("/api/v1/review", json={"diff": ""}).status_code == 422

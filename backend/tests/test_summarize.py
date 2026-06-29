"""AI summarization core + endpoint (Phase 4)."""
import pytest

from api import summarizer

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from api.deps import get_llm  # noqa: E402
from main import app  # noqa: E402


class _FakeLLM:
    def __init__(self):
        self.last_prompt = None

    def generate(self, prompt, temperature=0.2):
        self.last_prompt = prompt
        return "SUMMARY"


def test_context_from_entities():
    ctx = summarizer.context_from_entities(
        [{"name": "foo", "loc": 12}, {"name": "Bar"}]
    )
    assert "- foo (12 loc)" in ctx
    assert "- Bar" in ctx


def test_summarize_renders_prompt_and_calls_llm():
    llm = _FakeLLM()
    out = summarizer.summarize(llm, "a.py", "- foo", kind="file")
    assert out == "SUMMARY"
    assert "a.py" in llm.last_prompt and "- foo" in llm.last_prompt


def test_summarize_truncates_context():
    llm = _FakeLLM()
    summarizer.summarize(llm, "big.py", "x" * 20000)
    assert len(llm.last_prompt) < 20000 + 2000  # context capped before prompting


@pytest.fixture
def client_with_fake_llm(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    app.dependency_overrides[get_llm] = lambda: _FakeLLM()
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_llm, None)


def test_summarize_endpoint_with_inline_code(client_with_fake_llm):
    r = client_with_fake_llm.post(
        "/api/v1/summarize",
        json={"target": "snippet.py", "code": "def f():\n    return 1"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["summary"] == "SUMMARY"
    assert body["target"] == "snippet.py"

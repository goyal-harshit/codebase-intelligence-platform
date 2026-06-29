"""HTML risk-report builder + optional PDF behaviour (Phase 3)."""
import pytest

from api import report

RISKS = [
    {"type": "god_object", "severity": "high", "target": "Foo", "file": "a.py", "details": "40 methods"},
    {"type": "long_method", "severity": "low", "target": "bar", "file": "b.py", "details": "200 lines"},
]


def test_html_report_contains_summary_and_rows():
    html = report.build_html_report(RISKS, title="My Report")
    assert "<!DOCTYPE html>" in html
    assert "My Report" in html
    assert "2 finding(s)" in html
    assert "god_object" in html and "Foo" in html
    # Severity counts rendered (one high, one low).
    assert "sev-high" in html and "sev-low" in html


def test_html_report_escapes_content():
    html = report.build_html_report(
        [{"type": "x", "severity": "high", "target": "<script>", "file": "", "details": ""}]
    )
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_empty_report_is_valid():
    html = report.build_html_report([])
    assert "No risks detected." in html


def test_pdf_to_pdf_raises_clearly_when_unavailable():
    if report.pdf_available():
        pytest.skip("weasyprint installed; the unavailable path is not exercised here")
    with pytest.raises(RuntimeError, match="WeasyPrint"):
        report.to_pdf("<html></html>")


def test_format_findings_and_narrative_html():
    assert "god_object" in report.format_findings(RISKS)
    assert report.format_findings([]) == "- No risks detected."
    html = report.build_html_report(RISKS, narrative="Para one.\n\nPara two.")
    assert "Summary" in html and "Para one." in html and "Para two." in html


def test_build_narrative_calls_llm():
    class _FakeLLM:
        def generate(self, prompt, temperature=0.2):
            assert "god_object" in prompt  # findings made it into the prompt
            return "The codebase is mostly healthy."

    assert report.build_narrative(_FakeLLM(), RISKS).startswith("The codebase")


def test_report_endpoint_html(monkeypatch):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from main import app

    monkeypatch.delenv("API_KEY", raising=False)
    client = TestClient(app)
    r = client.get("/api/v1/report/risks", params={"format": "html"})
    # 200 with a graph backend, 503 without — but never a crash or 400.
    assert r.status_code in (200, 503)
    assert client.get("/api/v1/report/risks", params={"format": "docx"}).status_code == 400

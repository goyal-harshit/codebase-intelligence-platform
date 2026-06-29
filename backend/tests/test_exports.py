"""CSV/Excel export builders and endpoints (Phase 3)."""
import io

import pytest

from api import exports

RISKS = [
    {"type": "god_object", "severity": "high", "target": "Foo", "file": "a.py", "details": "40 methods"},
    {"type": "dead_code", "severity": "medium", "target": "bar", "file": "b.py", "details": "no callers"},
]
IMPACT = {
    "target": "a.py",
    "directly_affected": [{"name": "x", "file": "c.py", "hops": 1}],
    "transitively_affected": [{"name": "y", "file": "d.py", "hops": 2}],
}


def test_risks_to_rows_uses_stable_columns():
    headers, rows = exports.risks_to_rows(RISKS)
    assert headers == exports.RISK_HEADERS
    assert rows[0] == ["god_object", "high", "Foo", "a.py", "40 methods"]
    assert len(rows) == 2


def test_impact_to_rows_flattens_direct_and_transitive():
    headers, rows = exports.impact_to_rows(IMPACT)
    assert headers == exports.IMPACT_HEADERS
    assert ["direct", "x", "c.py", 1] in rows
    assert ["transitive", "y", "d.py", 2] in rows


def test_csv_roundtrip():
    headers, rows = exports.risks_to_rows(RISKS)
    body = exports.to_csv(headers, rows).decode("utf-8-sig")
    lines = body.splitlines()
    assert lines[0] == "type,severity,target,file,details"
    assert "god_object,high,Foo,a.py,40 methods" in lines


def test_xlsx_is_readable():
    openpyxl = pytest.importorskip("openpyxl")
    headers, rows = exports.risks_to_rows(RISKS)
    body = exports.to_xlsx(headers, rows, sheet_title="risks")
    wb = openpyxl.load_workbook(io.BytesIO(body))
    ws = wb.active
    assert ws.title == "risks"
    assert [c.value for c in ws[1]] == exports.RISK_HEADERS
    assert ws.cell(row=2, column=1).value == "god_object"


def test_render_rejects_unknown_format():
    with pytest.raises(ValueError):
        exports.render("pdf", ["a"], [["1"]])


def test_export_endpoint_rejects_bad_format(monkeypatch):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from main import app

    monkeypatch.delenv("API_KEY", raising=False)
    client = TestClient(app)
    r = client.get("/api/v1/export/risks", params={"format": "pdf"})
    assert r.status_code == 400

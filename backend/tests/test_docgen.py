"""Roadmap v1.3 tests — module skeletons, wiki assembly, LLM degrade, endpoints."""
from __future__ import annotations

import pytest

from docgen import DocGenerator, build_skeleton, build_wiki, purpose_narrative

FIXTURE = {
    "path": "src/app.py",
    "entities": [
        {"type": "function", "name": "main", "signature": "def main(argv)",
         "docstring": None, "line_start": 1, "line_end": 8},
        {"type": "class", "name": "App", "signature": "class App(Base)",
         "docstring": "Main application.\nSecond line ignored.", "line_start": 10, "line_end": 40},
        {"type": "method", "name": "run", "signature": "def run(self)",
         "docstring": "Run it.", "line_start": 12, "line_end": 20},
    ],
    "imports": ["os", "requests"],
    "used_by": ["src/cli.py"],
}


# -- skeleton ---------------------------------------------------------------

def test_skeleton_lists_inventory_and_dependencies():
    md = build_skeleton(FIXTURE)
    assert md.startswith("# `src/app.py`")
    assert "## Classes" in md and "`class App(Base)` (lines 10–40) — Main application." in md
    assert "## Functions" in md and "`def main(argv)` (lines 1–8)" in md
    assert "`def run(self)`" in md  # methods land under Functions
    assert "**Imports:** `os`, `requests`" in md
    assert "**Used by:** `src/cli.py`" in md
    assert "## Purpose" not in md  # no narrative -> pure inventory


def test_skeleton_with_purpose_and_empty_module():
    md = build_skeleton(dict(FIXTURE, purpose="Handles app startup."))
    assert "## Purpose" in md and "Handles app startup." in md

    empty = build_skeleton({"path": "src/empty.py", "entities": [], "imports": [], "used_by": []})
    assert "_None._" in empty and "_none recorded_" in empty


def test_build_wiki_has_index_and_all_pages():
    pages = [
        {"module": "src/app.py", "markdown": build_skeleton(FIXTURE)},
        {"module": "src/util.py", "markdown": "# `src/util.py`\n"},
    ]
    wiki = build_wiki(pages)
    assert wiki.startswith("# Project Wiki")
    assert "## Index" in wiki
    assert "- [`src/app.py`](#src-app-py)" in wiki
    assert "# `src/util.py`" in wiki and "# `src/app.py`" in wiki


# -- narrative degrade ------------------------------------------------------

class OkLLM:
    def generate(self, prompt, temperature=0.2):
        assert "src/app.py" in prompt and "def main(argv)" in prompt
        return "Boots the application."


class BadLLM:
    def generate(self, prompt, temperature=0.2):
        raise RuntimeError("llm down")


def test_purpose_narrative_uses_llm_and_degrades():
    assert purpose_narrative(FIXTURE, OkLLM()) == "Boots the application."
    assert purpose_narrative(FIXTURE, BadLLM()) is None  # graceful degrade


# -- generator over a fake graph -------------------------------------------

class FakeGraph:
    def query(self, command, params=None, language="cypher"):
        if "MATCH (f:File)" in command and "RETURN f.path" in command:
            return [{"path": "src/util.py"}, {"path": "src/app.py"}]
        if "IMPORTS" in command:
            return [{"name": "os"}]
        if "CALLS" in command:
            return [{"path": "src/cli.py"}]
        if "(e:Function" in command and params["path"] == "src/app.py":
            return [{"type": "function", "name": "main", "signature": "def main(argv)",
                     "docstring": None, "line_start": 1, "line_end": 8}]
        return []  # Class/Interface labels, and all of src/util.py


def test_generate_all_modules_sorted_and_filtered():
    gen = DocGenerator(FakeGraph())
    assert gen.list_modules() == ["src/app.py", "src/util.py"]

    pages = gen.generate()
    assert [p["module"] for p in pages] == ["src/app.py", "src/util.py"]
    assert "`def main(argv)`" in pages[0]["markdown"]

    # explicit selection filters and drops unknown paths
    pages = gen.generate(modules=["src/app.py", "no/such.py"])
    assert [p["module"] for p in pages] == ["src/app.py"]


def test_generate_narrative_on_and_degraded():
    gen = DocGenerator(FakeGraph())

    class AnyOkLLM:
        def generate(self, prompt, temperature=0.2):
            return "Purpose prose."

    with_llm = gen.generate(modules=["src/app.py"], narrative=True, llm=AnyOkLLM())
    assert "## Purpose" in with_llm[0]["markdown"]

    degraded = gen.generate(modules=["src/app.py"], narrative=True, llm=BadLLM())
    plain = gen.generate(modules=["src/app.py"])
    assert degraded[0]["markdown"] == plain[0]["markdown"]  # skeleton unchanged


# -- endpoints --------------------------------------------------------------

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from api.deps import get_graph_client  # noqa: E402
from main import app  # noqa: E402

client = TestClient(app)


def test_openapi_lists_docgen_routes():
    paths = client.get("/openapi.json").json()["paths"]
    for p in ["/api/v1/docgen/modules", "/api/v1/docgen/generate", "/api/v1/docgen/wiki"]:
        assert p in paths


def test_modules_degrades_to_503_without_graph():
    r = client.get("/api/v1/docgen/modules")
    assert r.status_code in (200, 503)
    if r.status_code == 503:
        assert "unavailable" in r.json()["detail"]


def test_endpoints_with_fake_graph():
    app.dependency_overrides[get_graph_client] = lambda: FakeGraph()
    try:
        r = client.get("/api/v1/docgen/modules")
        assert r.status_code == 200
        assert r.json() == {"modules": ["src/app.py", "src/util.py"], "total": 2}

        r = client.post("/api/v1/docgen/generate", json={"modules": ["src/app.py"]})
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1 and body["narrative"] is False
        assert body["pages"][0]["module"] == "src/app.py"
        assert "`def main(argv)`" in body["pages"][0]["markdown"]

        r = client.post("/api/v1/docgen/generate")  # body optional -> all modules
        assert r.status_code == 200 and r.json()["total"] == 2

        r = client.get("/api/v1/docgen/wiki")
        assert r.status_code == 200
        wiki = r.json()
        assert wiki["total"] == 2 and "## Index" in wiki["markdown"]
        assert "# `src/util.py`" in wiki["markdown"]
    finally:
        app.dependency_overrides.pop(get_graph_client, None)

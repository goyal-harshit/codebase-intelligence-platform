import os
from analysis import analyze_repository
from analysis import qa, webapp

SAMPLES = os.path.join(os.path.dirname(__file__), "samples")


def _a():
    return analyze_repository(SAMPLES, top_n=10, with_git=False)


def test_index_built():
    a = _a()
    assert a.index["entity_count"] > 0
    assert "communities" in a.index
    assert a.index["suggested_questions"]


def test_qa_explain_and_callers():
    a = _a()
    r = qa.answer(a.index, "what does validate_user do")
    assert r["kind"] == "entity"
    r2 = qa.answer(a.index, "who calls validate_user")
    assert r2["kind"] in ("callers", "entity")


def test_qa_file_and_search():
    a = _a()
    r = qa.answer(a.index, "what is in sample.py")
    assert r["kind"] == "file" and r["results"]
    r2 = qa.answer(a.index, "password")
    assert r2["results"]


def test_webapp_pages_render():
    a = _a()
    base = "/view/x"
    for fn in (webapp.overview_page(a), webapp.graph_page(a),
               webapp.risks_page(a), webapp.deps_page(a), webapp.hotspots_page(a)):
        assert "<h1>" in fn
    assert "<h1>" in webapp.modules_page(a, base)
    assert "<h1>" in webapp.functions_page(a, base)
    assert "<h1>" in webapp.ask_page(a, base, "validate_user")
    eid = next(iter(a.index["entities"]))
    assert "<h1>" in webapp.function_detail_page(a, eid, base)

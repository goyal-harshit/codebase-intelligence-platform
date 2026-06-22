import os

from analysis import analyze_repository
from analysis.report import render_html

SAMPLES = os.path.join(os.path.dirname(__file__), "samples")


def test_analyze_samples_overview():
    a = analyze_repository(SAMPLES, top_n=10, with_git=False)
    assert a.overview["functions_and_methods"] > 0
    assert a.overview["classes"] >= 2
    assert "python" in a.languages


def test_health_score_present():
    a = analyze_repository(SAMPLES, top_n=10, with_git=False)
    hs = a.health_score
    assert 0 <= hs["overall"] <= 100
    assert hs["grade"] in {"A", "B", "C", "D", "F"}


def test_complexity_picks_up_branches():
    a = analyze_repository(SAMPLES, top_n=10, with_git=False)
    names = {r["name"] for r in a.complexity["most_complex"]}
    assert "validate_user" in names


def test_call_graph_and_blast_radius():
    a = analyze_repository(SAMPLES, top_n=10, with_git=False)
    called = {r["name"] for r in a.call_graph["most_called_functions"]}
    # validate_user is called by Account.login and AdminAccount.login
    assert "validate_user" in called or a.call_graph["edges"] > 0


def test_risk_summary_keys():
    a = analyze_repository(SAMPLES, top_n=10, with_git=False)
    s = a.risks["summary"]
    for k in ("god_objects", "dead_code", "long_methods", "high_complexity",
              "shotgun_surgery", "deep_inheritance"):
        assert k in s


def test_dependencies_external_detected():
    a = analyze_repository(SAMPLES, top_n=10, with_git=False)
    pkgs = {r["package"] for r in a.dependencies["top_external"]}
    assert "os" in pkgs or "collections" in pkgs


def test_html_renders():
    a = analyze_repository(SAMPLES, top_n=10, with_git=False)
    html = render_html(a)
    assert "Codebase Intelligence Report" in html
    assert "Health Score" in html


def test_git_insights_on_self():
    # The project repo itself has git history in CI/local; tolerate absence.
    a = analyze_repository(SAMPLES, top_n=5, with_git=True)
    assert "available" in a.git


def test_graph_view_present():
    a = analyze_repository(SAMPLES, top_n=10, with_git=False)
    g = a.graph
    assert "nodes" in g and "links" in g
    assert g["node_count"] == len(g["nodes"])
    for n in g["nodes"]:
        assert {"id", "label", "group", "degree"} <= set(n)


def test_graph_renders_in_html():
    a = analyze_repository(SAMPLES, top_n=10, with_git=False)
    h = render_html(a)
    assert "Dependency Graph" in h
    assert "gcanvas" in h and "glegend" in h

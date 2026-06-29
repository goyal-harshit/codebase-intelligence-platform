from __future__ import annotations

import subprocess
from pathlib import Path

from analysis.hotspots import build_hotspots


class FakeGraph:
    def query(self, command, params=None, language="cypher"):
        assert "MATCH (f:Function)" in command
        return [
            {"file": str(self.repo / "a.py"), "complexity": 4, "loc": 12},
            {"file": str(self.repo / "a.py"), "complexity": 2, "loc": 7},
            {"file": str(self.repo / "b.py"), "complexity": 10, "loc": 20},
        ]


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def test_build_hotspots_ranks_churn_times_complexity(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_text("def a():\n    return 1\n")
    (repo / "b.py").write_text("def b():\n    return 1\n")
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "initial")
    (repo / "a.py").write_text("def a():\n    return 2\n")
    _git(repo, "add", "a.py")
    _git(repo, "commit", "-m", "touch a")

    graph = FakeGraph()
    graph.repo = repo

    result = build_hotspots(graph, str(repo), limit=10)

    assert result["available"] is True
    assert result["hotspots"][0]["file"] == "a.py"
    assert result["hotspots"][0]["churn"] == 2
    assert result["hotspots"][0]["total_complexity"] == 6
    assert result["hotspots"][0]["score"] == 12

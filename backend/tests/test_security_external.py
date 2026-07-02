"""Bandit/Ruff integration for the security scan (tools run for real)."""
import shutil
import subprocess
import sys

import pytest

from security_scan import scan_repository
from security_scan import external


def _tool_usable(module: str) -> bool:
    try:
        subprocess.run(
            [sys.executable, "-m", module, "--version"],
            capture_output=True, timeout=30,
        )
        return True
    except Exception:  # noqa: BLE001
        return False


VULN_PY = '''import subprocess

password = "hunter2-really-long"

def run(cmd):
    subprocess.call(cmd, shell=True)
'''


@pytest.fixture()
def vuln_repo(tmp_path):
    (tmp_path / "app.py").write_text(VULN_PY)
    return str(tmp_path)


def test_builtin_findings_carry_source(vuln_repo):
    result = scan_repository(vuln_repo)
    assert result["total"] > 0
    assert all(f["source"] == "builtin" for f in result["findings"])
    assert "tools" not in result  # external not requested


@pytest.mark.skipif(not _tool_usable("bandit"), reason="bandit not installed")
def test_bandit_findings_merged(vuln_repo):
    result = scan_repository(vuln_repo, external=True)
    assert result["tools"]["bandit"] is True
    bandit = [f for f in result["findings"] if f["source"] == "bandit"]
    assert bandit, "bandit should flag shell=True / hardcoded password"
    # Normalized shape + no raw code echoed.
    for f in bandit:
        assert f["rule"].startswith("bandit:")
        assert f["severity"] in ("critical", "high", "medium", "low")
        assert f["file"] == "app.py"
        assert f["snippet"] == ""


@pytest.mark.skipif(not _tool_usable("ruff"), reason="ruff not installed")
def test_ruff_security_rules_merged(vuln_repo):
    result = scan_repository(vuln_repo, external=True)
    assert result["tools"]["ruff"] is True
    ruff = [f for f in result["findings"] if f["source"] == "ruff"]
    assert any(f["rule"].startswith("ruff:S") for f in ruff)
    # shell=True (S602) is one of the codes promoted to high severity.
    assert any(f["severity"] == "high" for f in ruff)


def test_merged_results_stay_sorted_and_counted(vuln_repo):
    result = scan_repository(vuln_repo, external=True)
    sev_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    ranks = [sev_rank[f["severity"]] for f in result["findings"]]
    assert ranks == sorted(ranks)
    assert result["total"] == len(result["findings"])
    assert sum(result["by_severity"].values()) == result["total"]


def test_degrades_when_tools_unusable(vuln_repo, monkeypatch):
    monkeypatch.setattr(external, "_run_json", lambda *a, **k: None)
    result = scan_repository(vuln_repo, external=True)
    assert result["tools"] == {"bandit": False, "ruff": False}
    # Builtin findings still served.
    assert result["total"] > 0
    assert all(f["source"] == "builtin" for f in result["findings"])

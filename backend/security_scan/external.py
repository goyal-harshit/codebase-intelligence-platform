"""Proven-tool SAST integration: Bandit and Ruff security rules.

The builtin regex scanner casts a wide, language-agnostic net; these adapters
add depth for Python by shelling out to Bandit (full run) and Ruff restricted
to its flake8-bandit ``S`` rules. Both are invoked as ``python -m ...`` from
the current interpreter's environment with JSON output, and both degrade to
"no findings, tool marked unavailable" on any failure (not installed, timeout,
unparseable output) so /api/v1/security keeps working from the builtin rules
alone.

Findings are normalized to the builtin scanner's dict shape plus a ``source``
key ("bandit" / "ruff"; builtin findings carry "builtin").
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

_TIMEOUT_SECONDS = 120

# Bandit severities map 1:1; Ruff S-rules carry no severity, so they surface
# as medium except a few high-signal codes.
_BANDIT_SEVERITY = {"HIGH": "high", "MEDIUM": "medium", "LOW": "low"}
_RUFF_HIGH = {"S102", "S105", "S106", "S107", "S602", "S605"}  # exec, hardcoded pw, shell=True
_RUFF_LOW = {"S101"}  # assert used


def _run_json(args: list[str], cwd: str | None = None):
    """Run a tool and parse its stdout as JSON; None on any failure.

    Non-zero exit alone is not failure — both tools exit 1 when findings
    exist — only unusable output is.
    """
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_SECONDS,
            cwd=cwd,
        )
        return json.loads(proc.stdout)
    except Exception:  # noqa: BLE001 - tool optional; degrade gracefully
        return None


def _rel(path: str, repo_path: str) -> str:
    try:
        return os.path.relpath(path, repo_path).replace("\\", "/")
    except ValueError:  # different drive on Windows
        return path.replace("\\", "/")


def run_bandit(repo_path: str) -> list[dict] | None:
    """Bandit findings for *repo_path*, or None if the tool is unusable."""
    data = _run_json(
        [sys.executable, "-m", "bandit", "-r", repo_path, "-f", "json", "-q"]
    )
    if not isinstance(data, dict) or "results" not in data:
        return None
    findings = []
    for r in data["results"]:
        findings.append({
            "rule": f"bandit:{r.get('test_id', '?')}",
            "severity": _BANDIT_SEVERITY.get(r.get("issue_severity", ""), "medium"),
            "file": _rel(r.get("filename", "?"), repo_path),
            "line": r.get("line_number", 0),
            "message": r.get("issue_text", r.get("test_name", "")),
            "snippet": "",  # bandit echoes raw code; omit rather than risk leaking a secret
            "source": "bandit",
        })
    return findings


def run_ruff(repo_path: str) -> list[dict] | None:
    """Ruff flake8-bandit (S) findings, or None if the tool is unusable."""
    data = _run_json(
        [
            sys.executable, "-m", "ruff", "check", repo_path,
            "--select", "S", "--output-format", "json",
            "--no-cache", "--exit-zero", "--isolated",
        ]
    )
    if not isinstance(data, list):
        return None
    findings = []
    for r in data:
        code = r.get("code") or "?"
        severity = "high" if code in _RUFF_HIGH else "low" if code in _RUFF_LOW else "medium"
        findings.append({
            "rule": f"ruff:{code}",
            "severity": severity,
            "file": _rel(r.get("filename", "?"), repo_path),
            "line": (r.get("location") or {}).get("row", 0),
            "message": r.get("message", ""),
            "snippet": "",
            "source": "ruff",
        })
    return findings


def run_external_tools(repo_path: str) -> tuple[list[dict], dict[str, bool]]:
    """All external-tool findings plus per-tool availability flags."""
    findings: list[dict] = []
    tools: dict[str, bool] = {}
    for name, runner in (("bandit", run_bandit), ("ruff", run_ruff)):
        result = runner(repo_path)
        tools[name] = result is not None
        findings.extend(result or [])
    return findings, tools

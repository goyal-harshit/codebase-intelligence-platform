"""Phase 11 SAST tests — rule hits, false-positive gating, repo scan + sort."""
from __future__ import annotations

from pathlib import Path

from security_scan import SecurityScanner, scan_repository


def _rules_hit(text: str) -> set[str]:
    return {f["rule"] for f in SecurityScanner().scan_text("x.py", text)}


def test_detects_hardcoded_secret():
    assert "hardcoded_secret" in _rules_hit('password = "s3cr3tValue!"')


def test_ignores_env_lookup_and_placeholders():
    hits = _rules_hit('password = os.getenv("DB_PASSWORD")\napi_key = "changeme"')
    assert "hardcoded_secret" not in hits


def test_detects_weak_hash_and_eval_and_verify_false():
    hits = _rules_hit(
        "import hashlib\n"
        "h = hashlib.md5(data)\n"
        "eval(user_input)\n"
        "requests.get(url, verify=False)\n"
    )
    assert {"weak_hash", "dangerous_eval", "tls_verification_disabled"} <= hits


def test_sql_injection_requires_sql_keyword():
    assert "sql_injection" in _rules_hit('cursor.execute("SELECT * FROM t WHERE id=" + uid)')
    # execute() without SQL keywords should not trip the rule
    assert "sql_injection" not in _rules_hit('cursor.execute("PRAGMA foreign_keys" + x)')


def test_command_injection_shell_true():
    assert "command_injection" in _rules_hit("subprocess.run(cmd, shell=True)")
    assert "command_injection" in _rules_hit("os.system(user_cmd)")


def test_aws_key_is_critical():
    findings = SecurityScanner().scan_text("c.py", 'key = "AKIAIOSFODNN7EXAMPLE0"')
    aws = [f for f in findings if f["rule"] == "aws_access_key"]
    assert aws and aws[0]["severity"] == "critical"


def test_snippet_is_redacted():
    finding = SecurityScanner().scan_text("c.py", 'secret = "supersecretlongtoken"')[0]
    assert "supersecretlongtoken" not in finding["snippet"]
    assert "***" in finding["snippet"]


def test_scan_repository_sorts_and_summarizes(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_text('password = "hunter2hunter"\nx = hashlib.md5(b"a")\n')
    (repo / "note.txt").write_text('password = "hunter2hunter"\n')  # non-scannable ext
    result = scan_repository(str(repo))

    assert result["total"] >= 2
    # highest severity first
    sev = [f["severity"] for f in result["findings"]]
    assert sev == sorted(sev, key={"critical": 0, "high": 1, "medium": 2, "low": 3}.get)
    # note.txt is not a scannable extension
    assert all(f["file"] == "a.py" for f in result["findings"])

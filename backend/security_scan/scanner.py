"""Regex-driven static security scanner (roadmap Phase 11).

Conservative by design — each rule pairs a pattern with optional gating
(``contains_any`` / ``exclude_if_any``) to keep false positives low. Rules are
line-oriented; findings carry file, line, message, and a redacted snippet.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Iterable, Optional

from ast_parser.repo_walker import walk_repository

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

# Only scan text source/config; skip binaries and lockfiles/minified blobs.
_SCAN_EXTS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".java", ".rb", ".php", ".cs",
    ".c", ".cpp", ".h", ".rs", ".kt", ".scala", ".sh", ".bash", ".ps1",
    ".yml", ".yaml", ".json", ".toml", ".ini", ".cfg", ".conf", ".env",
    ".xml", ".properties", ".tf", ".sql",
}
_MAX_FILE_BYTES = 2_000_000
_MAX_FINDINGS = 1000
_MAX_PER_FILE = 50
_MAX_SNIPPET = 200

# Values that look like secrets but are placeholders / env lookups.
_SECRET_EXCLUDE = (
    "os.getenv", "os.environ", "getenv", "environ[", "process.env", "config(",
    "changeme", "change-me", "example", "your-", "your_", "placeholder",
    "dummy", "redacted", "xxxx", "<", "${", "{{", "test", "sample", "fake",
)


@dataclass(frozen=True)
class Rule:
    name: str
    severity: str
    message: str
    pattern: re.Pattern
    contains_any: tuple[str, ...] = field(default=())      # line must also contain one
    exclude_if_any: tuple[str, ...] = field(default=())    # skip if line contains one


def _rules() -> list[Rule]:
    return [
        Rule(
            "aws_access_key", "critical",
            "Possible AWS access key id committed in source.",
            re.compile(r"AKIA[0-9A-Z]{16}"),
        ),
        Rule(
            "private_key", "critical",
            "Private key material embedded in source.",
            re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"),
        ),
        Rule(
            "hardcoded_secret", "high",
            "Hardcoded credential/secret literal — load from env/secret store instead.",
            re.compile(
                r"""(?ix)\b(pass(word|wd)?|secret|api[_-]?key|access[_-]?token|
                    auth[_-]?token|client[_-]?secret|private[_-]?key)\b
                    \s*[:=]\s*['"][^'"\s]{8,}['"]""",
                re.VERBOSE,
            ),
            exclude_if_any=_SECRET_EXCLUDE,
        ),
        Rule(
            "sql_injection", "high",
            "SQL built by string concatenation/format — use parameterized queries.",
            re.compile(r"(?i)(execute|executemany|cursor\.execute)\s*\(\s*(f['\"]|['\"].*['\"]\s*(\+|%|\.format))"),
            contains_any=("select", "insert", "update", "delete", "where", "from "),
        ),
        Rule(
            "command_injection", "high",
            "Shell command with shell=True or os.system — risk of command injection.",
            re.compile(r"(?i)(os\.system\s*\(|subprocess\.(?:call|run|Popen)\s*\([^)]*shell\s*=\s*True)"),
        ),
        Rule(
            "dangerous_eval", "high",
            "Dynamic code execution (eval/exec) on untrusted input is dangerous.",
            re.compile(r"(?<![\w.])(eval|exec)\s*\("),
            exclude_if_any=("# noqa", "ast.literal_eval"),
        ),
        Rule(
            "insecure_deserialization", "medium",
            "Unsafe deserialization (pickle.loads / yaml.load without SafeLoader).",
            re.compile(r"(?i)(pickle\.loads?\s*\(|yaml\.load\s*\((?!.*SafeLoader))"),
        ),
        Rule(
            "weak_hash", "medium",
            "Weak/broken hash algorithm (MD5/SHA1) — use SHA-256+ for security uses.",
            re.compile(r"(?i)hashlib\.(md5|sha1)\s*\("),
        ),
        Rule(
            "tls_verification_disabled", "medium",
            "TLS certificate verification disabled (verify=False).",
            re.compile(r"(?i)verify\s*=\s*False"),
        ),
        Rule(
            "debug_enabled", "low",
            "Debug mode enabled — ensure it is off in production.",
            re.compile(r"(?i)\bDEBUG\s*=\s*True\b"),
        ),
    ]


def _is_scannable(rel: str) -> bool:
    name = os.path.basename(rel)
    if name == ".env" or name.startswith(".env."):
        return True
    return os.path.splitext(name)[1].lower() in _SCAN_EXTS


def _redact(line: str) -> str:
    snippet = line.strip()[:_MAX_SNIPPET]
    # Redact the inside of quoted literals so we never echo the secret itself.
    return re.sub(r"(['\"])([^'\"]{4,})(['\"])", lambda m: m.group(1) + "***" + m.group(3), snippet)


def _scan_text(rel: str, text: str, rules: list[Rule]) -> list[dict]:
    findings: list[dict] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if len(line) > 2000:  # skip minified / generated one-liners
            continue
        low = line.lower()
        for rule in rules:
            if rule.exclude_if_any and any(x in low for x in rule.exclude_if_any):
                continue
            if rule.contains_any and not any(x in low for x in rule.contains_any):
                continue
            if rule.pattern.search(line):
                findings.append({
                    "rule": rule.name,
                    "severity": rule.severity,
                    "file": rel,
                    "line": lineno,
                    "message": rule.message,
                    "snippet": _redact(line),
                    "source": "builtin",
                })
                if len(findings) >= _MAX_PER_FILE:
                    return findings
    return findings


class SecurityScanner:
    def __init__(self, rules: Optional[Iterable[Rule]] = None) -> None:
        self.rules = list(rules) if rules is not None else _rules()

    def scan_text(self, rel_path: str, text: str) -> list[dict]:
        return _scan_text(rel_path, text, self.rules)

    def scan_repository(self, repo_path: str) -> dict:
        findings: list[dict] = []
        files_scanned = 0
        for abs_path in walk_repository(repo_path, only_supported=False):
            rel = os.path.relpath(abs_path, repo_path).replace("\\", "/")
            if not _is_scannable(rel):
                continue
            try:
                if os.path.getsize(abs_path) > _MAX_FILE_BYTES:
                    continue
                with open(abs_path, "r", encoding="utf-8", errors="ignore") as fh:
                    text = fh.read()
            except OSError:
                continue
            if "\x00" in text[:1024]:  # binary
                continue
            files_scanned += 1
            findings.extend(self.scan_text(rel, text))
            if len(findings) >= _MAX_FINDINGS:
                findings = findings[:_MAX_FINDINGS]
                break

        findings.sort(key=lambda f: (SEVERITY_ORDER.get(f["severity"], 9), f["file"], f["line"]))
        by_severity: dict[str, int] = {}
        for f in findings:
            by_severity[f["severity"]] = by_severity.get(f["severity"], 0) + 1
        return {
            "repo_path": repo_path,
            "files_scanned": files_scanned,
            "findings": findings,
            "total": len(findings),
            "by_severity": by_severity,
        }


def scan_repository(repo_path: str, external: bool = False) -> dict:
    """Scan with the builtin rules; ``external=True`` also runs Bandit and
    Ruff's security (S) rules and merges their findings (tagged by source)."""
    result = SecurityScanner().scan_repository(repo_path)
    if not external:
        return result

    from .external import run_external_tools  # local import: subprocess machinery

    extra, tools = run_external_tools(repo_path)
    findings = result["findings"] + extra
    findings.sort(key=lambda f: (SEVERITY_ORDER.get(f["severity"], 9), f["file"], f["line"]))
    by_severity: dict[str, int] = {}
    for f in findings:
        by_severity[f["severity"]] = by_severity.get(f["severity"], 0) + 1
    return {
        **result,
        "findings": findings,
        "total": len(findings),
        "by_severity": by_severity,
        "tools": tools,
    }

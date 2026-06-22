"""Optional local-LLM integration (Ollama by default; any OpenAI-compatible
endpoint works). Pure stdlib HTTP - no SDK required. Degrades gracefully:
if no model is reachable, callers fall back to the built-in Q&A.

Config via env:
  LLM_BASE_URL   default http://localhost:11434/v1   (Ollama OpenAI-compatible)
  LLM_MODEL      default qwen2.5-coder:7b
  LLM_API_KEY    optional (for hosted OpenAI-compatible endpoints)
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1").rstrip("/")
MODEL = os.environ.get("LLM_MODEL", "qwen2.5-coder:7b")
API_KEY = os.environ.get("LLM_API_KEY", "")


def available(timeout=1.5) -> bool:
    """True if an LLM endpoint answers. Cheap, never raises."""
    for url in (BASE_URL + "/models", BASE_URL.replace("/v1", "") + "/api/tags"):
        try:
            req = urllib.request.Request(url, headers=_headers())
            with urllib.request.urlopen(req, timeout=timeout) as r:
                if r.status == 200:
                    return True
        except Exception:
            continue
    return False


def _headers():
    h = {"Content-Type": "application/json"}
    if API_KEY:
        h["Authorization"] = "Bearer " + API_KEY
    return h


def chat(messages, temperature=0.2, timeout=90) -> str:
    """OpenAI-compatible chat completion. Raises on failure."""
    body = json.dumps({"model": MODEL, "messages": messages,
                       "temperature": temperature, "stream": False}).encode()
    req = urllib.request.Request(BASE_URL + "/chat/completions", data=body,
                                 headers=_headers(), method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode())
    return data["choices"][0]["message"]["content"].strip()


SYSTEM = (
    "You are a senior engineer helping a new joiner understand an unfamiliar "
    "codebase. Answer ONLY from the provided context (functions, files, call "
    "relationships). Be concrete: cite file paths and function names. If the "
    "context is insufficient, say so plainly. Keep it tight and practical."
)


def explain(question: str, context: str, temperature=0.2) -> str:
    return chat([{"role": "system", "content": SYSTEM},
                 {"role": "user",
                  "content": "Context:\n%s\n\nQuestion: %s" % (context, question)}],
                temperature=temperature)


def build_context(index: dict, qa_result: dict, max_chars=6000) -> str:
    """Turn the built-in retrieval result into compact LLM context."""
    ents = index.get("entities", {})
    lines = []
    ent = qa_result.get("entity")
    if ent and ent["id"] in ents:
        e = ents[ent["id"]]
        lines.append("FOCUS %s `%s` in %s:%d" % (e["type"], e["signature"] or e["name"], e["file"], e["line"]))
        if e["docstring"]:
            lines.append("  doc: " + e["docstring"][:400])
        if e["raw_code"] if "raw_code" in e else None:
            pass
        cers = [ents[c]["name"] for c in e["callers"][:12] if c in ents]
        cees = [ents[c]["name"] for c in e["callees"][:12] if c in ents]
        if cers:
            lines.append("  called by: " + ", ".join(cers))
        if cees:
            lines.append("  calls: " + ", ".join(cees))
    for r in (qa_result.get("results") or [])[:15]:
        e = ents.get(r["id"])
        if not e:
            lines.append("- %s (%s) %s:%d" % (r["name"], r["type"], r["file"], r["line"]))
            continue
        d = (" - " + e["docstring"][:120]) if e["docstring"] else ""
        lines.append("- %s `%s` %s:%d%s" % (e["type"], e["signature"] or e["name"], e["file"], e["line"], d))
    text = "\n".join(lines)
    return text[:max_chars] if text else "No matching code found in the index."

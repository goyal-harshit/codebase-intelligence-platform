"""Built-in, no-setup Q&A over the code index. Deterministic, offline.

Understands questions like:
  - "what does X do" / "explain X"      -> entity summary (signature, doc, callers/callees)
  - "where is X" / "find X"             -> matching entities with file:line
  - "who calls X"                       -> callers
  - "what does X call" / "callees of X" -> callees
  - "what is in <file>"                 -> entities in that file
  - anything else                       -> keyword search over names + docstrings
"""
from __future__ import annotations

import re


def answer(index: dict, question: str) -> dict:
    q = (question or "").strip()
    if not q:
        return {"kind": "empty", "answer": "Ask about a function, file, or concept.", "results": []}
    ql = q.lower()
    ents = index.get("entities", {})
    files = index.get("files", {})

    # file lookup
    m = re.search(r"(?:what(?:'s| is)? in|contents? of|show me)\s+(.+)", ql)
    if m or re.search(r"\.\w{1,4}$", q.strip()):
        target = (m.group(1) if m else q).strip().strip("?'\" ")
        fmatch = _match_file(files, target)
        if fmatch:
            ids = files[fmatch]
            rows = [ents[i] for i in ids]
            rows.sort(key=lambda e: e["line"])
            return {"kind": "file", "file": fmatch,
                    "answer": "%s contains %d entities." % (fmatch, len(rows)),
                    "results": [_brief(e) for e in rows]}

    # who calls X
    m = re.search(r"(?:who calls|callers of|what calls)\s+(.+)", ql)
    if m:
        name = m.group(1).strip().strip("?'\" ")
        hits = _by_name(ents, name)
        if hits:
            e = hits[0]
            callers = [ents[c] for c in e["callers"] if c in ents]
            return {"kind": "callers", "entity": _brief(e),
                    "answer": "%s is called by %d place(s)." % (e["name"], len(callers)),
                    "results": [_brief(c) for c in callers]}

    # what does X call
    m = re.search(r"(?:what does|callees of|what funcs? does)\s+(.+?)\s+call", ql)
    if m:
        name = m.group(1).strip().strip("?'\" ")
        hits = _by_name(ents, name)
        if hits:
            e = hits[0]
            callees = [ents[c] for c in e["callees"] if c in ents]
            return {"kind": "callees", "entity": _brief(e),
                    "answer": "%s calls %d function(s)." % (e["name"], len(callees)),
                    "results": [_brief(c) for c in callees]}

    # explain / what does X do  / where is X / find X
    m = re.search(r"(?:explain|what does|what is|describe)\s+(.+?)(?:\s+do)?[?]?$", ql)
    m2 = re.search(r"(?:where is|where's|find|locate|show)\s+(.+)", ql)
    name = None
    if m:
        name = m.group(1)
    elif m2:
        name = m2.group(1)
    if name:
        name = name.strip().strip("?'\" ")
        hits = _by_name(ents, name)
        if hits:
            if len(hits) == 1 or hits[0]["name"].lower() == name.lower():
                return _explain(ents, hits[0])
            return {"kind": "matches",
                    "answer": "%d entities match '%s':" % (len(hits), name),
                    "results": [_brief(e) for e in hits[:25]]}

    # fallback keyword search
    return _search(ents, q)


def _explain(ents, e):
    callers = [ents[c] for c in e["callers"] if c in ents]
    callees = [ents[c] for c in e["callees"] if c in ents]
    parts = []
    parts.append("%s `%s`" % (e["type"].capitalize(), e["signature"] or e["name"]))
    parts.append("Defined in %s:%d" % (e["file"], e["line"]))
    if e["docstring"]:
        parts.append("Doc: " + e["docstring"])
    parts.append("Cyclomatic complexity %d, %d lines." % (e["complexity"], e["loc"]))
    if callers:
        parts.append("Called by %d place(s)." % len(callers))
    else:
        parts.append("No in-repo callers (entry point or public API).")
    if callees:
        parts.append("Calls %d function(s)." % len(callees))
    return {"kind": "entity", "entity": _brief(e), "answer": "  ".join(parts),
            "callers": [_brief(c) for c in callers],
            "callees": [_brief(c) for c in callees],
            "results": []}


def _search(ents, q):
    terms = [t for t in re.split(r"\W+", q.lower()) if len(t) > 2]
    scored = []
    for e in ents.values():
        hay = (e["name"] + " " + e["signature"] + " " + e["docstring"] + " " + e["file"]).lower()
        score = sum(hay.count(t) for t in terms)
        if e["name"].lower() in terms:
            score += 5
        if score:
            scored.append((score, e))
    scored.sort(key=lambda x: (x[0], len(x[1]["callers"])), reverse=True)
    if not scored:
        return {"kind": "none", "answer": "No matches for '%s'." % q, "results": []}
    return {"kind": "search", "answer": "%d matches for '%s':" % (len(scored), q),
            "results": [_brief(e) for _, e in scored[:25]]}


def _by_name(ents, name):
    name = name.lower()
    exact = [e for e in ents.values() if e["name"].lower() == name]
    if exact:
        exact.sort(key=lambda e: len(e["callers"]), reverse=True)
        return exact
    part = [e for e in ents.values() if name in e["name"].lower()]
    part.sort(key=lambda e: (e["name"].lower() != name, -len(e["callers"])))
    return part


def _match_file(files, target):
    target = target.replace("\\", "/").strip()
    if target in files:
        return target
    cand = [f for f in files if f.replace("\\", "/").endswith(target)]
    if cand:
        return min(cand, key=len)
    cand = [f for f in files if target in f.replace("\\", "/")]
    return min(cand, key=len) if cand else None


def _brief(e):
    return {"id": e["id"], "name": e["name"], "type": e["type"],
            "file": e["file"], "line": e["line"],
            "signature": e["signature"], "complexity": e["complexity"],
            "callers": len(e["callers"]), "callees": len(e["callees"])}

"""Per-module documentation from the code graph (roadmap v1.3).

The graph already stores every parsed entity with its ``file_path``,
``signature``, ``docstring`` and line range, plus File-[:IMPORTS]->Module and
cross-file CALLS edges. :class:`DocGenerator` groups that by source file
("module") and :func:`build_skeleton` renders a deterministic markdown page
per module — no LLM required.

:func:`purpose_narrative` optionally layers one short prose "Purpose" section
per module on top (one bounded LLM call per module, capped at
:data:`MAX_NARRATIVE_MODULES` per request). It returns ``None`` on any
failure so the skeleton is served unchanged when the model is unreachable —
same degrade pattern as ``refactoring.recommend_narrative``.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from graph_db import ArcadeDBClient
    from llm import LLMClient

# Hard cap on LLM calls per generate request; modules beyond this get the
# deterministic skeleton only.
MAX_NARRATIVE_MODULES = 20

# Overall bound on pages per request (wiki stays a bounded payload).
MAX_MODULES = 200

# Entity vertex labels that carry documentable code entities.
_ENTITY_LABELS = ("Class", "Interface", "Function")

# entity.type values rendered under "Classes" (rest go under "Functions").
_CLASS_TYPES = {"class", "implementation", "interface"}


class DocGenerator:
    """Collects per-module facts from the graph and renders wiki pages."""

    def __init__(self, client: "ArcadeDBClient") -> None:
        self.client = client

    # -- graph access --------------------------------------------------------

    def list_modules(self) -> list[str]:
        """Distinct source-file paths the graph knows about, sorted."""
        rows = self.client.query("MATCH (f:File) RETURN f.path AS path") or []
        return sorted({r["path"] for r in rows if r.get("path")})

    def collect(self, path: str) -> dict:
        """All facts needed to document one module (source file)."""
        entities: list[dict] = []
        for label in _ENTITY_LABELS:
            rows = self.client.query(
                f"MATCH (e:{label} {{file_path: $path}}) "
                "RETURN e.type AS type, e.name AS name, e.signature AS signature, "
                "e.docstring AS docstring, e.line_start AS line_start, "
                "e.line_end AS line_end",
                params={"path": path},
            ) or []
            entities.extend(rows)
        entities.sort(key=lambda e: (e.get("line_start") or 0, e.get("name") or ""))

        imports = self.client.query(
            "MATCH (f:File {path: $path})-[:IMPORTS]->(m:Module) RETURN m.name AS name",
            params={"path": path},
        ) or []

        used_by = self.client.query(
            "MATCH (g:File)-[:CONTAINS]->(a)-[:CALLS]->(b)<-[:CONTAINS]-"
            "(f:File {path: $path}) WHERE g.path <> $path "
            "RETURN DISTINCT g.path AS path",
            params={"path": path},
        ) or []

        return {
            "path": path,
            "entities": entities,
            "imports": sorted({r["name"] for r in imports if r.get("name")}),
            "used_by": sorted({r["path"] for r in used_by if r.get("path")}),
        }

    # -- page generation -----------------------------------------------------

    def generate(
        self,
        modules: Optional[list[str]] = None,
        narrative: bool = False,
        llm: Optional["LLMClient"] = None,
        max_modules: int = MAX_MODULES,
    ) -> list[dict]:
        """Render one page per module: ``[{"module": path, "markdown": md}]``.

        ``modules`` filters (unknown paths are dropped); otherwise every module
        the graph knows is documented, capped at ``max_modules``. With
        ``narrative=True`` and an LLM, the first :data:`MAX_NARRATIVE_MODULES`
        pages get a prose Purpose section — best-effort only.
        """
        available = self.list_modules()
        if modules is not None:
            known = set(available)
            wanted = [m for m in modules if m in known]
        else:
            wanted = available
        wanted = wanted[:max_modules]

        pages: list[dict] = []
        for i, path in enumerate(wanted):
            mod = self.collect(path)
            if narrative and llm is not None and i < MAX_NARRATIVE_MODULES:
                mod["purpose"] = purpose_narrative(mod, llm)
            pages.append({"module": path, "markdown": build_skeleton(mod)})
        return pages


def build_skeleton(module: dict) -> str:
    """Deterministic markdown page for one module dict (see ``collect``).

    If ``module["purpose"]`` is set (LLM pass succeeded) a Purpose section is
    included; otherwise the page is pure inventory.
    """
    path = module["path"]
    lines: list[str] = [f"# `{path}`", ""]

    purpose = module.get("purpose")
    if purpose:
        lines += ["## Purpose", "", purpose.strip(), ""]

    classes = [e for e in module.get("entities", []) if e.get("type") in _CLASS_TYPES]
    functions = [e for e in module.get("entities", []) if e.get("type") not in _CLASS_TYPES]

    lines.append("## Classes")
    lines.append("")
    if classes:
        lines += [_entity_line(e) for e in classes]
    else:
        lines.append("_None._")
    lines.append("")

    lines.append("## Functions")
    lines.append("")
    if functions:
        lines += [_entity_line(e) for e in functions]
    else:
        lines.append("_None._")
    lines.append("")

    lines.append("## Dependencies")
    lines.append("")
    imports = module.get("imports") or []
    used_by = module.get("used_by") or []
    lines.append(
        "**Imports:** " + (", ".join(f"`{m}`" for m in imports) if imports else "_none recorded_")
    )
    lines.append(
        "**Used by:** " + (", ".join(f"`{p}`" for p in used_by) if used_by else "_none recorded_")
    )
    lines.append("")
    return "\n".join(lines)


def build_wiki(pages: list[dict]) -> str:
    """Concatenate pages into a single wiki document with an index section."""
    out: list[str] = ["# Project Wiki", "", "## Index", ""]
    if pages:
        out += [f"- [`{p['module']}`](#{_slug(p['module'])})" for p in pages]
    else:
        out.append("_No documented modules._")
    out.append("")
    for p in pages:
        out += ["---", "", p["markdown"].rstrip(), ""]
    return "\n".join(out)


def purpose_narrative(module: dict, llm: "LLMClient", max_entities: int = 20) -> Optional[str]:
    """One bounded LLM call producing a short prose purpose for a module.

    Returns ``None`` on any failure (model down, empty output) so callers keep
    serving the deterministic skeleton unchanged.
    """
    names = [
        e.get("signature") or e.get("name") or "?"
        for e in module.get("entities", [])[:max_entities]
    ]
    prompt = (
        "You are writing developer documentation. In 2-4 sentences, describe "
        f"the purpose of the module `{module['path']}` based only on the facts "
        "below. Be concrete; do not invent behavior.\n\n"
        f"Entities: {'; '.join(names) or '(none)'}\n"
        f"Imports: {', '.join(module.get('imports') or []) or '(none)'}\n"
        f"Used by: {', '.join(module.get('used_by') or []) or '(none)'}"
    )
    try:
        return llm.generate(prompt, temperature=0.2).strip() or None
    except Exception:  # noqa: BLE001 - LLM optional; degrade gracefully
        return None


def _entity_line(e: dict) -> str:
    label = e.get("signature") or e.get("name") or "?"
    line = f"- `{label}`"
    start, end = e.get("line_start"), e.get("line_end")
    if start:
        line += f" (lines {start}–{end or start})"
    doc = (e.get("docstring") or "").strip().splitlines()
    if doc and doc[0].strip():
        line += f" — {doc[0].strip()}"
    return line


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")

"""Second-pass resolution of unresolved `calls` edges to real entity IDs.

When several entities share a name (e.g. ``method`` defined on two classes), a
bare last-segment match would cross-wire them. This resolver uses the call's
receiver hint (``self``/``this``/``cls`` or a class name, captured by the
parser) plus the caller's enclosing class to pick the right target, falling back
to the previous "first candidate, flag ambiguous" behaviour only when it still
cannot tell them apart.
"""
from __future__ import annotations

from typing import Optional

from .parser import CodeEntity, CodeRelationship

_SELF_RECEIVERS = {"self", "this", "cls"}


class SymbolResolver:
    def resolve(self, entities: list[CodeEntity],
                relationships: list[CodeRelationship]) -> list[CodeRelationship]:
        name_index: dict[str, list[str]] = {}
        for e in entities:
            name_index.setdefault(e.name, []).append(e.id)

        # entity id -> name of the class that directly CONTAINS it (if any)
        class_of: dict[str, str] = {}
        entity_type: dict[str, str] = {e.id: e.type for e in entities}
        entity_name: dict[str, str] = {e.id: e.name for e in entities}
        for rel in relationships:
            if rel.type == "contains" and entity_type.get(rel.source_id) == "class":
                class_of[rel.target_id] = entity_name.get(rel.source_id, "")

        resolved: list[CodeRelationship] = []
        for rel in relationships:
            if rel.type in ("calls", "inherits_from") and "unresolved_name" in rel.metadata:
                candidates = name_index.get(rel.metadata["unresolved_name"], [])
                target, flag = self._pick(rel, candidates, class_of)
                if target is not None:
                    rel.target_id = target
                if flag:
                    rel.metadata[flag] = True
            resolved.append(rel)
        return resolved

    def _pick(self, rel: CodeRelationship, candidates: list[str],
              class_of: dict[str, str]) -> tuple[Optional[str], Optional[str]]:
        """Return (target_id, metadata_flag)."""
        if not candidates:
            return None, "external"
        if len(candidates) == 1:
            return candidates[0], None

        receiver = rel.metadata.get("receiver")
        if receiver:
            # self/this/cls -> a sibling method in the caller's own class wins.
            if receiver in _SELF_RECEIVERS:
                caller_class = class_of.get(rel.source_id)
                if caller_class:
                    same = [c for c in candidates if class_of.get(c) == caller_class]
                    if len(same) == 1:
                        return same[0], None
            # Foo.bar() -> prefer a candidate defined on class Foo.
            on_receiver = [c for c in candidates if class_of.get(c) == receiver]
            if len(on_receiver) == 1:
                return on_receiver[0], None

        # Genuinely undecidable: keep the old deterministic choice + flag it.
        return candidates[0], "ambiguous"

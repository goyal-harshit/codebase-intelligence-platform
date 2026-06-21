"""Second-pass resolution of unresolved `calls` edges to real entity IDs."""
from __future__ import annotations

from .parser import CodeEntity, CodeRelationship


class SymbolResolver:
    def resolve(self, entities: list[CodeEntity],
                relationships: list[CodeRelationship]) -> list[CodeRelationship]:
        name_index: dict[str, list[str]] = {}
        for e in entities:
            name_index.setdefault(e.name, []).append(e.id)

        resolved: list[CodeRelationship] = []
        for rel in relationships:
            if rel.type == "calls" and "unresolved_name" in rel.metadata:
                candidates = name_index.get(rel.metadata["unresolved_name"], [])
                if len(candidates) == 1:
                    rel.target_id = candidates[0]
                elif len(candidates) > 1:
                    rel.target_id = candidates[0]
                    rel.metadata["ambiguous"] = True
                else:
                    rel.metadata["external"] = True
            resolved.append(rel)
        return resolved

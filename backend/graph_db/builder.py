"""Bulk ingestion of parsed entities/relationships into the graph.

Uses parameterized ``UNWIND $rows`` batches rather than string-interpolated
Cypher. This avoids escaping/injection bugs entirely and lets ArcadeDB plan a
single statement per batch instead of one round-trip per row.
"""
from __future__ import annotations

import os
from collections import defaultdict
from typing import TYPE_CHECKING, Iterable

from ast_parser import CodeEntity, CodeRelationship

if TYPE_CHECKING:
    from .client import ArcadeDBClient

# Parser entity.type  ->  graph vertex label.
LABEL_MAP = {
    "function": "Function",
    "method": "Function",
    "class": "Class",
    "implementation": "Class",
    "interface": "Interface",
    "module": "Module",
}
DEFAULT_LABEL = "Function"

# Properties copied verbatim from a CodeEntity onto its vertex.
ENTITY_PROPS = [
    "id", "type", "name", "file_path", "language",
    "line_start", "line_end", "signature", "docstring",
    "cyclomatic_complexity", "lines_of_code",
]


def label_for(entity_type: str) -> str:
    return LABEL_MAP.get(entity_type, DEFAULT_LABEL)


class GraphBuilder:
    def __init__(self, client: "ArcadeDBClient", batch_size: int = 500) -> None:
        self.client = client
        self.batch_size = batch_size
        # id -> label, populated as entities are ingested; used to type edge MATCHes
        # and to drop edges whose endpoints aren't real vertices (external calls).
        self.id_labels: dict[str, str] = {}

    # -- public API --------------------------------------------------------

    def build(self, entities: list[CodeEntity], relationships: list[CodeRelationship]) -> dict:
        """Full ingest: entities, File + Module nodes, then relationships."""
        self.ingest_entities(entities)
        files = self.ingest_files(entities, relationships)
        imports = self.ingest_imports(relationships)
        edges = self.ingest_relationships(relationships)
        return {
            "entities": len(entities),
            "files": files,
            "imports": imports,
            "edges": edges,
        }

    def ingest_entities(self, entities: Iterable[CodeEntity]) -> None:
        by_label: dict[str, list[dict]] = defaultdict(list)
        for e in entities:
            label = label_for(e.type)
            self.id_labels[e.id] = label
            by_label[label].append({p: getattr(e, p) for p in ENTITY_PROPS})

        for label, rows in by_label.items():
            self._create_vertices(label, ENTITY_PROPS, rows)

    def ingest_files(self, entities: Iterable[CodeEntity],
                     relationships: Iterable[CodeRelationship]) -> int:
        """Create one File vertex per distinct path and CONTAINS edges to the
        top-level entities defined in it (entities never CONTAINed by another)."""
        contained = {r.target_id for r in relationships if r.type == "contains"}
        files: dict[str, list[str]] = defaultdict(list)
        for e in entities:
            files.setdefault(e.file_path, [])
            if e.id not in contained:
                files[e.file_path].append(e.id)

        file_rows = []
        for path in files:
            fid = _file_id(path)
            self.id_labels[fid] = "File"
            file_rows.append({"id": fid, "path": path, "name": os.path.basename(path)})
        self._create_vertices("File", ["id", "path", "name"], file_rows)

        edge_rows = [
            {"source_id": _file_id(path), "target_id": eid}
            for path, eids in files.items()
            for eid in eids
        ]
        self._create_edges_grouped("CONTAINS", edge_rows)
        return len(file_rows)

    def ingest_imports(self, relationships: Iterable[CodeRelationship]) -> int:
        """Create Module vertices for imported modules and File-[:IMPORTS]->Module
        edges. Import sources are file paths, targets are external module names —
        so this is handled separately from entity-to-entity relationships."""
        imports = [r for r in relationships if r.type == "imports"]
        if not imports:
            return 0

        # Ensure a File vertex exists for every importing path (a file with only
        # imports and no entities won't have been created by ingest_files).
        file_rows = []
        for path in {r.source_id for r in imports}:
            fid = _file_id(path)
            if fid not in self.id_labels:
                self.id_labels[fid] = "File"
                file_rows.append({"id": fid, "path": path, "name": os.path.basename(path)})
        self._create_vertices("File", ["id", "path", "name"], file_rows)

        module_rows = []
        for name in {r.target_id for r in imports}:
            mid = _module_id(name)
            if mid not in self.id_labels:
                self.id_labels[mid] = "Module"
                module_rows.append({"id": mid, "name": name})
        self._create_vertices("Module", ["id", "name"], module_rows)

        edge_rows = [
            {"source_id": _file_id(r.source_id), "target_id": _module_id(r.target_id)}
            for r in {(r.source_id, r.target_id): r for r in imports}.values()  # dedupe
        ]
        return self._create_edges_grouped("IMPORTS", edge_rows)

    def ingest_relationships(self, relationships: Iterable[CodeRelationship]) -> int:
        """Create entity-to-entity edges, skipping imports (handled separately)
        and any whose endpoints aren't known vertices (e.g. external calls)."""
        by_type: dict[str, list[dict]] = defaultdict(list)
        for r in relationships:
            if r.type == "imports":
                continue
            if r.source_id in self.id_labels and r.target_id in self.id_labels:
                by_type[r.type.upper()].append(
                    {"source_id": r.source_id, "target_id": r.target_id}
                )

        total = 0
        for edge_type, rows in by_type.items():
            total += self._create_edges_grouped(edge_type, rows)
        return total

    # -- internals ---------------------------------------------------------

    def _create_vertices(self, label: str, props: list[str], rows: list[dict]) -> None:
        if not rows:
            return
        assignments = ", ".join(f"{p}: row.{p}" for p in props)
        cypher = f"UNWIND $rows AS row CREATE (n:{label} {{{assignments}}})"
        for batch in _chunks(rows, self.batch_size):
            self.client.command(cypher, params={"rows": batch})

    def _create_edges_grouped(self, edge_type: str, rows: list[dict]) -> int:
        """Group edges by (source_label, target_label) so each MATCH is typed
        and index-backed, then UNWIND-create each group in batches."""
        if not rows:
            return 0
        groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for r in rows:
            key = (self.id_labels[r["source_id"]], self.id_labels[r["target_id"]])
            groups[key].append(r)

        total = 0
        for (src_label, tgt_label), group in groups.items():
            cypher = (
                f"UNWIND $rows AS row "
                f"MATCH (a:{src_label} {{id: row.source_id}}), "
                f"(b:{tgt_label} {{id: row.target_id}}) "
                f"CREATE (a)-[:{edge_type}]->(b)"
            )
            for batch in _chunks(group, self.batch_size):
                self.client.command(cypher, params={"rows": batch})
                total += len(batch)
        return total


def _file_id(path: str) -> str:
    return f"file:{path}"


def _module_id(name: str) -> str:
    return f"module:{name}"


def _chunks(seq: list, size: int):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]

"""Graph database layer (Phase 2): ArcadeDB ingestion + incremental updates."""
from .client import ArcadeDBClient, ArcadeDBError
from .schema import apply_schema, schema_statements, VERTEX_TYPES, EDGE_TYPES
from .builder import GraphBuilder, label_for, LABEL_MAP
from .incremental import IncrementalUpdater, FileHashStore

__all__ = [
    "ArcadeDBClient", "ArcadeDBError",
    "apply_schema", "schema_statements", "VERTEX_TYPES", "EDGE_TYPES",
    "GraphBuilder", "label_for", "LABEL_MAP",
    "IncrementalUpdater", "FileHashStore",
]

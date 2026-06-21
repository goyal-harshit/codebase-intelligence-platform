"""Phase 2 tests.

The unit tests run offline against a recording fake client — they assert that
the builder emits well-formed, parameterized Cypher and correctly maps labels,
synthesizes File nodes, and drops external edges. A live-ArcadeDB integration
test is gated behind the ARCADEDB_INTEGRATION env var.
"""
import os

import pytest

from ast_parser import CodeEntity, CodeRelationship
from graph_db import GraphBuilder, label_for, schema_statements
from graph_db.builder import _file_id


class FakeClient:
    """Records every command(...) call instead of hitting a server."""

    def __init__(self):
        self.calls = []  # list of (cypher, params, language)

    def command(self, command, params=None, language="cypher"):
        self.calls.append((command, params or {}, language))
        return []

    def query(self, command, params=None, language="cypher"):
        return []


SAMPLE_ENTITIES = [
    CodeEntity(id="c1", type="class", name="Account", file_path="a.py",
               language="python", line_start=1, line_end=20),
    CodeEntity(id="m1", type="method", name="login", file_path="a.py",
               language="python", line_start=2, line_end=8),
    CodeEntity(id="f1", type="function", name="helper", file_path="b.py",
               language="python", line_start=1, line_end=4),
]
SAMPLE_RELS = [
    CodeRelationship("c1", "m1", "contains"),
    CodeRelationship("m1", "f1", "calls", metadata={"unresolved_name": "helper"}),
    # external/unresolved call: target is a bare name, not a known entity id
    CodeRelationship("f1", "print", "calls", metadata={"external": True}),
]


def test_label_mapping():
    assert label_for("function") == "Function"
    assert label_for("method") == "Function"
    assert label_for("class") == "Class"
    assert label_for("interface") == "Interface"
    assert label_for("mystery") == "Function"  # default


def test_schema_statements_well_formed():
    stmts = schema_statements()
    assert any("CREATE VERTEX TYPE Function" in s for s in stmts)
    assert any("CREATE EDGE TYPE CALLS" in s for s in stmts)
    assert any("INDEX" in s and "File" in s for s in stmts)


def test_inserts_are_parameterized_not_interpolated():
    client = FakeClient()
    GraphBuilder(client).build(SAMPLE_ENTITIES, SAMPLE_RELS)
    # Every write must use UNWIND $rows with params, never inline values.
    for cypher, params, _ in client.calls:
        assert "UNWIND $rows" in cypher
        assert "rows" in params and isinstance(params["rows"], list)


def test_entities_grouped_by_label():
    client = FakeClient()
    GraphBuilder(client).build(SAMPLE_ENTITIES, SAMPLE_RELS)
    vertex_calls = [c for c in client.calls if "CREATE (n:" in c[0]]
    labels = {c[0].split("CREATE (n:")[1].split(" ")[0].rstrip("{") for c in vertex_calls}
    assert "Class" in labels
    assert "Function" in labels  # both helper (function) and login (method)
    assert "File" in labels


def test_file_nodes_and_contains_edges():
    client = FakeClient()
    builder = GraphBuilder(client)
    files = builder.ingest_entities(SAMPLE_ENTITIES) or None
    n_files = builder.ingest_files(SAMPLE_ENTITIES, SAMPLE_RELS)
    assert n_files == 2  # a.py and b.py
    assert builder.id_labels[_file_id("a.py")] == "File"


def test_external_call_edge_dropped():
    client = FakeClient()
    builder = GraphBuilder(client)
    builder.ingest_entities(SAMPLE_ENTITIES)  # populate id_labels first
    edges = builder.ingest_relationships(SAMPLE_RELS)
    # contains (c1->m1) + calls (m1->f1) are valid; f1->print is external -> dropped
    assert edges == 2


def test_edge_match_is_typed():
    client = FakeClient()
    builder = GraphBuilder(client)
    builder.ingest_entities(SAMPLE_ENTITIES)
    builder.ingest_relationships(SAMPLE_RELS)
    edge_calls = [c[0] for c in client.calls if "CREATE (a)-[:" in c[0]]
    # MATCHes must carry vertex labels so they hit the id index.
    assert all("MATCH (a:" in c and "(b:" in c for c in edge_calls)


@pytest.mark.skipif(
    not os.getenv("ARCADEDB_INTEGRATION"),
    reason="set ARCADEDB_INTEGRATION=1 with a live ArcadeDB to run",
)
def test_integration_roundtrip():
    from graph_db import ArcadeDBClient, apply_schema

    client = ArcadeDBClient(database="codebase_test")
    if client.database_exists():
        client.drop_database()
    client.create_database()
    apply_schema(client)
    GraphBuilder(client).build(SAMPLE_ENTITIES, SAMPLE_RELS)
    result = client.query("MATCH (f:Function) RETURN count(f) AS n")
    assert result[0]["n"] == 2
    client.drop_database()

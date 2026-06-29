"""SymbolResolver disambiguation tests (offline, no tree-sitter)."""
from ast_parser.parser import CodeEntity, CodeRelationship
from ast_parser.symbol_resolver import SymbolResolver


def _entity(eid, name, etype):
    return CodeEntity(id=eid, type=etype, name=name, file_path=f"{eid}.py",
                      language="python", line_start=1, line_end=2)


def _build():
    # Two classes A and B each defining run(); A.caller() makes the calls.
    entities = [
        _entity("A", "A", "class"),
        _entity("A.run", "run", "method"),
        _entity("A.caller", "caller", "method"),
        _entity("B", "B", "class"),
        _entity("B.run", "run", "method"),
    ]
    contains = [
        CodeRelationship("A", "A.run", "contains"),
        CodeRelationship("A", "A.caller", "contains"),
        CodeRelationship("B", "B.run", "contains"),
    ]
    return entities, contains


def _resolve(entities, rels):
    return SymbolResolver().resolve(entities, rels)


def test_self_call_resolves_to_own_class():
    entities, rels = _build()
    rels.append(CodeRelationship("A.caller", "run", "calls",
                                 metadata={"unresolved_name": "run", "receiver": "self"}))
    out = _resolve(entities, rels)
    call = [r for r in out if r.type == "calls"][0]
    assert call.target_id == "A.run"
    assert "ambiguous" not in call.metadata


def test_qualified_call_resolves_to_named_class():
    entities, rels = _build()
    rels.append(CodeRelationship("A.caller", "run", "calls",
                                 metadata={"unresolved_name": "run", "receiver": "B"}))
    out = _resolve(entities, rels)
    call = [r for r in out if r.type == "calls"][0]
    assert call.target_id == "B.run"


def test_unqualified_ambiguous_call_flags_ambiguous():
    entities, rels = _build()
    rels.append(CodeRelationship("A.caller", "run", "calls",
                                 metadata={"unresolved_name": "run"}))
    out = _resolve(entities, rels)
    call = [r for r in out if r.type == "calls"][0]
    assert call.metadata.get("ambiguous") is True


def test_single_candidate_resolves_cleanly():
    entities, rels = _build()
    rels.append(CodeRelationship("A.caller", "caller", "calls",
                                 metadata={"unresolved_name": "caller", "receiver": "self"}))
    out = _resolve(entities, rels)
    call = [r for r in out if r.type == "calls"][-1]
    assert call.target_id == "A.caller"
    assert "ambiguous" not in call.metadata


def test_unknown_name_flagged_external():
    entities, rels = _build()
    rels.append(CodeRelationship("A.caller", "nope", "calls",
                                 metadata={"unresolved_name": "nope"}))
    out = _resolve(entities, rels)
    call = [r for r in out if r.type == "calls"][-1]
    assert call.metadata.get("external") is True

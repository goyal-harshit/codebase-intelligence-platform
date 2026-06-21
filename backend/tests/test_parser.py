import os

from ast_parser import UniversalParser, SymbolResolver

SAMPLES = os.path.join(os.path.dirname(__file__), "samples")


def _parse(name):
    return UniversalParser().parse_file(os.path.join(SAMPLES, name))


def test_parses_python_functions_and_class():
    entities, _ = _parse("sample.py")
    names = {e.name for e in entities}
    assert {"helper", "validate_user", "Account", "login"} <= names
    assert any(e.type == "class" and e.name == "Account" for e in entities)


def test_python_docstring_and_complexity():
    entities, _ = _parse("sample.py")
    vu = next(e for e in entities if e.name == "validate_user")
    assert vu.cyclomatic_complexity >= 3
    helper = next(e for e in entities if e.name == "helper")
    assert helper.docstring == "Double a number."


def test_detects_calls():
    entities, rels = _parse("sample.py")
    assert any(r.type == "calls" for r in rels)


def test_symbol_resolution_links_call():
    entities, rels = _parse("sample.py")
    resolved = SymbolResolver().resolve(entities, rels)
    helper_id = next(e.id for e in entities if e.name == "helper")
    assert any(r.type == "calls" and r.target_id == helper_id for r in resolved)


def test_parses_javascript():
    entities, _ = _parse("sample.js")
    names = {e.name for e in entities}
    assert "validateUser" in names
    assert "Account" in names


def test_unsupported_extension_returns_empty():
    p = UniversalParser()
    assert p.detect_language("foo.unknownext") is None

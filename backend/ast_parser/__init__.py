"""AST parsing engine (Phase 1)."""
from .parser import (
    CodeEntity,
    CodeRelationship,
    UniversalParser,
    LANGUAGE_MAP,
)
from .repo_walker import walk_repository, file_hash
from .symbol_resolver import SymbolResolver


def parse_repository(repo_path: str):
    """Parse an entire repo: returns (entities, resolved_relationships)."""
    parser = UniversalParser()
    all_entities = []
    all_rels = []
    for path in walk_repository(repo_path):
        try:
            entities, rels = parser.parse_file(path)
        except Exception:
            continue
        all_entities.extend(entities)
        all_rels.extend(rels)
    resolved = SymbolResolver().resolve(all_entities, all_rels)
    return all_entities, resolved


__all__ = [
    "CodeEntity", "CodeRelationship", "UniversalParser", "LANGUAGE_MAP",
    "walk_repository", "file_hash", "SymbolResolver", "parse_repository",
]

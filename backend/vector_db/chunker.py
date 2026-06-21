"""AST-aware chunking: one chunk == one complete entity (function/class/method).

Never splits mid-statement — each chunk is a whole parsed entity, turned into a
rich text blob for embedding plus filterable metadata.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ast_parser import CodeEntity


class CodeChunker:
    def chunk_entity(self, entity: "CodeEntity") -> dict:
        text = (
            f"# {entity.type}: {entity.name}\n"
            f"# File: {entity.file_path}\n"
            f"# Language: {entity.language}\n"
            f"{entity.signature}\n"
            f"{entity.docstring}\n"
            f"{entity.raw_code}"
        )
        return {
            "id": entity.id,
            "text": text,
            "metadata": {
                "entity_type": entity.type,
                "name": entity.name,
                "file_path": entity.file_path,
                "language": entity.language,
                "complexity": entity.cyclomatic_complexity,
                "loc": entity.lines_of_code,
            },
        }

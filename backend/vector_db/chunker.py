"""AST-aware chunking: one chunk == one complete entity (function/class/method).

Never splits mid-statement — each chunk is a whole parsed entity, turned into a
rich text blob for embedding plus filterable metadata.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ast_parser import CodeEntity


class CodeChunker:
    # The embedder truncates to a token window anyway (see EMBED_MAX_TOKENS,
    # default 256 tokens ≈ ~1k chars for code). Feeding a 10k-char blob just makes
    # the tokenizer scan characters it will immediately drop, so cap the text at a
    # generous char budget first. The signal — header, signature, docstring, body
    # head — is all at the front, so tail truncation is cheap on quality.
    MAX_CHARS = 4000

    def chunk_entity(self, entity: "CodeEntity") -> dict:
        text = (
            f"# {entity.type}: {entity.name}\n"
            f"# File: {entity.file_path}\n"
            f"# Language: {entity.language}\n"
            f"{entity.signature}\n"
            f"{entity.docstring}\n"
            f"{entity.raw_code}"
        )
        if len(text) > self.MAX_CHARS:
            text = text[: self.MAX_CHARS]
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

"""Language-agnostic AST parser built on tree-sitter.

Extracts CodeEntity (functions/classes/methods) and CodeRelationship
(contains/calls) objects from any supported source file.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from typing import Optional

from tree_sitter_languages import get_parser

LANGUAGE_MAP = {
    ".py": "python", ".js": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "tsx", ".go": "go",
    ".rs": "rust", ".java": "java", ".rb": "ruby",
    ".php": "php", ".c": "c", ".cpp": "cpp", ".cs": "c_sharp",
}

ENTITY_NODE_TYPES = {
    "python": {"function_definition": "function", "class_definition": "class"},
    "javascript": {"function_declaration": "function", "class_declaration": "class",
                   "method_definition": "method", "arrow_function": "function"},
    "typescript": {"function_declaration": "function", "class_declaration": "class",
                   "interface_declaration": "interface", "method_definition": "method"},
    "tsx": {"function_declaration": "function", "class_declaration": "class",
            "method_definition": "method"},
    "go": {"function_declaration": "function", "method_declaration": "method",
           "type_declaration": "class"},
    "rust": {"function_item": "function", "struct_item": "class",
             "impl_item": "implementation"},
    "java": {"method_declaration": "method", "class_declaration": "class",
             "interface_declaration": "interface"},
}

BRANCH_TYPES = {
    "if_statement", "for_statement", "while_statement", "case_clause",
    "catch_clause", "conditional_expression", "and", "or",
    "elif_clause", "except_clause", "&&", "||",
}

CALL_NODE_TYPES = {"call", "call_expression", "method_invocation"}

IMPORT_NODE_TYPES = {
    "python": {"import_statement", "import_from_statement"},
    "javascript": {"import_statement"},
    "typescript": {"import_statement"},
    "tsx": {"import_statement"},
    "java": {"import_declaration"},
}


@dataclass
class CodeEntity:
    id: str
    type: str
    name: str
    file_path: str
    language: str
    line_start: int
    line_end: int
    signature: str = ""
    docstring: str = ""
    cyclomatic_complexity: int = 1
    lines_of_code: int = 0
    raw_code: str = ""


@dataclass
class CodeRelationship:
    source_id: str
    target_id: str
    type: str
    metadata: dict = field(default_factory=dict)


class UniversalParser:
    def __init__(self) -> None:
        self._parser_cache: dict = {}

    def _get_parser(self, language: str):
        if language not in self._parser_cache:
            self._parser_cache[language] = get_parser(language)
        return self._parser_cache[language]

    def detect_language(self, file_path: str) -> Optional[str]:
        return LANGUAGE_MAP.get(os.path.splitext(file_path)[1])

    def parse_file(self, file_path: str) -> tuple[list[CodeEntity], list[CodeRelationship]]:
        language = self.detect_language(file_path)
        if not language:
            return [], []
        with open(file_path, "rb") as f:
            source_code = f.read()
        return self.parse_source(source_code, file_path, language)

    def parse_source(self, source_code: bytes, file_path: str,
                     language: str) -> tuple[list[CodeEntity], list[CodeRelationship]]:
        parser = self._get_parser(language)
        tree = parser.parse(source_code)
        entities: list[CodeEntity] = []
        relationships: list[CodeRelationship] = []
        entity_types = ENTITY_NODE_TYPES.get(language, {})
        self._walk(tree.root_node, source_code, file_path, language,
                   entity_types, entities, relationships, parent_id=None)
        return entities, relationships

    def _walk(self, node, source_code, file_path, language, entity_types,
              entities, relationships, parent_id):
        if node.type in entity_types:
            name_node = node.child_by_field_name("name")
            name = self._text(name_node, source_code) if name_node else "anonymous"
            entity_id = self._make_id(file_path, name, node.start_point[0])
            entities.append(CodeEntity(
                id=entity_id,
                type=entity_types[node.type],
                name=name,
                file_path=file_path,
                language=language,
                line_start=node.start_point[0] + 1,
                line_end=node.end_point[0] + 1,
                lines_of_code=node.end_point[0] - node.start_point[0] + 1,
                signature=self._signature(node, source_code),
                docstring=self._docstring(node, source_code, language),
                cyclomatic_complexity=self._complexity(node),
                raw_code=self._text(node, source_code)[:2000],
            ))
            if parent_id:
                relationships.append(CodeRelationship(parent_id, entity_id, "contains"))
            parent_id = entity_id

            if entity_types[node.type] == "class":
                for base in self._base_class_names(node, source_code, language):
                    relationships.append(CodeRelationship(
                        entity_id, base, "inherits_from",
                        metadata={"unresolved_name": base},
                    ))

        if node.type in CALL_NODE_TYPES:
            callee = self._call_target(node, source_code)
            if callee and parent_id:
                relationships.append(CodeRelationship(
                    parent_id, callee, "calls",
                    metadata={"unresolved_name": callee},
                ))

        if node.type in IMPORT_NODE_TYPES.get(language, set()):
            for module in self._import_targets(node, source_code, language):
                relationships.append(CodeRelationship(
                    file_path, module, "imports",
                    metadata={"unresolved_name": module, "import": True},
                ))

        for child in node.children:
            self._walk(child, source_code, file_path, language, entity_types,
                       entities, relationships, parent_id)

    @staticmethod
    def _text(node, source_code) -> str:
        if node is None:
            return ""
        return source_code[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

    @staticmethod
    def _make_id(file_path: str, name: str, line: int) -> str:
        return hashlib.sha256(f"{file_path}:{name}:{line}".encode()).hexdigest()[:16]

    def _signature(self, node, source_code) -> str:
        params = node.child_by_field_name("parameters")
        name_node = node.child_by_field_name("name")
        name = self._text(name_node, source_code)
        return f"{name}{self._text(params, source_code)}" if params else name

    def _docstring(self, node, source_code, language) -> str:
        if language != "python":
            return ""
        body = node.child_by_field_name("body")
        if not body or not body.children:
            return ""
        first = body.children[0]
        if first.type == "expression_statement" and first.children and \
                first.children[0].type == "string":
            return self._text(first.children[0], source_code).strip("\"'")[:500]
        return ""

    def _call_target(self, node, source_code) -> Optional[str]:
        fn = node.child_by_field_name("function") or node.child_by_field_name("name")
        if fn is None:
            return None
        text = self._text(fn, source_code)
        return text.split(".")[-1].split("(")[0].strip() or None

    def _base_class_names(self, node, source_code, language) -> list[str]:
        """Names of classes this class extends (last path component only)."""
        if language == "python":
            sup = node.child_by_field_name("superclasses")
            if not sup:
                return []
            return [
                self._text(ch, source_code).split(".")[-1]
                for ch in sup.children
                if ch.type in ("identifier", "attribute")
            ]
        if language in ("javascript", "typescript", "tsx"):
            for ch in node.children:
                if ch.type == "class_heritage":
                    ident = self._first_identifier(ch, source_code)
                    return [ident] if ident else []
            return []
        if language == "java":
            sup = node.child_by_field_name("superclass")
            if sup:
                ident = self._first_identifier(sup, source_code)
                return [ident] if ident else []
            return []
        return []

    def _import_targets(self, node, source_code, language) -> list[str]:
        """Top-level module name(s) of an import statement."""
        if language == "python":
            if node.type == "import_statement":
                names = []
                for ch in node.children:
                    if ch.type == "dotted_name":
                        names.append(self._text(ch, source_code).split(".")[0])
                    elif ch.type == "aliased_import":
                        dn = ch.child_by_field_name("name")
                        if dn:
                            names.append(self._text(dn, source_code).split(".")[0])
                return names
            mod = node.child_by_field_name("module_name")
            if mod:
                return [self._text(mod, source_code).lstrip(".").split(".")[0]]
            return []
        if language in ("javascript", "typescript", "tsx"):
            src = node.child_by_field_name("source")
            if src:
                return [self._text(src, source_code).strip("\"'")]
            return []
        return []

    def _first_identifier(self, node, source_code):
        if node.type in ("identifier", "type_identifier"):
            return self._text(node, source_code)
        for ch in node.children:
            found = self._first_identifier(ch, source_code)
            if found:
                return found
        return None

    @staticmethod
    def _complexity(node) -> int:
        count = 1

        def visit(n):
            nonlocal count
            if n.type in BRANCH_TYPES:
                count += 1
            for c in n.children:
                visit(c)

        visit(node)
        return count

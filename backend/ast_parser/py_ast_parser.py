"""Pure-stdlib Python parser using the built-in `ast` module.

Fallback for when tree-sitter isn't installed. Produces the same CodeEntity /
CodeRelationship objects as the tree-sitter parser, for .py files only.
"""
from __future__ import annotations

import ast
import hashlib

from .parser import CodeEntity, CodeRelationship

_BRANCH = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try,
           ast.With, ast.AsyncWith, ast.BoolOp, ast.IfExp,
           ast.comprehension, ast.ExceptHandler)


def _id(file_path, name, line, col=0):
    return hashlib.sha256(f"{file_path}:{name}:{line}:{col}".encode()).hexdigest()[:16]


def _complexity(node):
    count = 1
    for n in ast.walk(node):
        if isinstance(n, _BRANCH):
            count += 1
        elif isinstance(n, ast.BoolOp):
            count += len(n.values) - 1
    return count


def _signature(node):
    try:
        args = [a.arg for a in node.args.args]
        if node.args.vararg:
            args.append("*" + node.args.vararg.arg)
        if node.args.kwarg:
            args.append("**" + node.args.kwarg.arg)
        return f"{node.name}({', '.join(args)})"
    except Exception:
        return getattr(node, "name", "")


def parse_python_source(source: bytes, file_path: str):
    text = source.decode("utf-8", "replace")
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return [], []
    lines = text.splitlines()
    entities, rels = [], []

    def emit(node, kind, parent_id):
        name = getattr(node, "name", "anonymous")
        line = node.lineno
        end = getattr(node, "end_lineno", line)
        eid = _id(file_path, name, line - 1, node.col_offset)
        doc = ast.get_docstring(node) or "" if isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) else ""
        raw = "\n".join(lines[line - 1:end])[:2000]
        entities.append(CodeEntity(
            id=eid, type=kind, name=name, file_path=file_path, language="python",
            line_start=line, line_end=end, lines_of_code=end - line + 1,
            signature=_signature(node) if kind != "class" else name,
            docstring=doc[:500], cyclomatic_complexity=_complexity(node), raw_code=raw,
        ))
        if parent_id:
            rels.append(CodeRelationship(parent_id, eid, "contains"))
        return eid

    def visit(node, parent_id, enclosing_func):
        new_func = enclosing_func
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            kind = "method" if _is_method(node, parent_id) else "function"
            eid = emit(node, kind, parent_id)
            parent_id = eid
            new_func = eid
        elif isinstance(node, ast.ClassDef):
            eid = emit(node, "class", parent_id)
            for base in node.bases:
                bname = _name_of(base)
                if bname:
                    rels.append(CodeRelationship(eid, bname, "inherits_from",
                                                 metadata={"unresolved_name": bname}))
            parent_id = eid
            new_func = None
        elif isinstance(node, ast.Call) and enclosing_func:
            callee = _name_of(node.func)
            if callee:
                rels.append(CodeRelationship(enclosing_func, callee, "calls",
                                             metadata={"unresolved_name": callee}))
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name.split(".")[0] for a in node.names]
            elif node.module:
                mods = [node.module.split(".")[0]]
            for m in mods:
                rels.append(CodeRelationship(file_path, m, "imports",
                                             metadata={"unresolved_name": m, "import": True}))

        for child in ast.iter_child_nodes(node):
            visit(child, parent_id, new_func)

    def _is_method(node, parent_id):
        return parent_id is not None and any(
            e.id == parent_id and e.type == "class" for e in entities)

    visit(tree, None, None)
    return entities, rels


def _name_of(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None

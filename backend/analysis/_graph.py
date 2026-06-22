"""Minimal directed-graph helpers (stdlib only) replacing the bits of networkx
that the analysis engine uses. Keeps the project dependency-free."""
from __future__ import annotations


class _DegreeView:
    """Iterable of (node, degree) pairs that is also callable: dv(n) -> degree."""

    def __init__(self, counts):
        self._counts = counts

    def __call__(self, n):
        return self._counts.get(n, 0)

    def __iter__(self):
        return iter(self._counts.items())


class DiGraph:
    def __init__(self):
        self._succ = {}
        self._pred = {}

    def add_node(self, n):
        self._succ.setdefault(n, set())
        self._pred.setdefault(n, set())

    def add_nodes_from(self, it):
        for n in it:
            self.add_node(n)

    def add_edge(self, a, b):
        self.add_node(a)
        self.add_node(b)
        self._succ[a].add(b)
        self._pred[b].add(a)

    @property
    def nodes(self):
        return list(self._succ.keys())

    def successors(self, n):
        return list(self._succ.get(n, ()))

    def predecessors(self, n):
        return list(self._pred.get(n, ()))

    def number_of_edges(self):
        return sum(len(s) for s in self._succ.values())

    @property
    def in_degree(self):
        return _DegreeView({n: len(p) for n, p in self._pred.items()})

    @property
    def out_degree(self):
        return _DegreeView({n: len(s) for n, s in self._succ.items()})

    def reverse(self, copy=False):
        r = DiGraph()
        r._succ = {n: set(p) for n, p in self._pred.items()}
        r._pred = {n: set(s) for n, s in self._succ.items()}
        return r


def descendants(g, source):
    """All nodes reachable from source (excluding source)."""
    seen = set()
    stack = list(g.successors(source))
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        stack.extend(g.successors(n))
    seen.discard(source)
    return seen


def simple_cycles(g):
    """Yield simple cycles (Johnson-style, simplified) as node lists.

    Sufficient for small module-dependency graphs. Caps work to stay fast.
    """
    nodes = g.nodes
    index = {n: i for i, n in enumerate(nodes)}
    found = []
    seen_signatures = set()

    def dfs(start, current, path, visited):
        if len(found) >= 1000:
            return
        for nxt in g.successors(current):
            if nxt == start and len(path) >= 2:
                sig = frozenset(path)
                if sig not in seen_signatures:
                    seen_signatures.add(sig)
                    found.append(list(path))
            elif nxt not in visited and index[nxt] > index[start]:
                visited.add(nxt)
                path.append(nxt)
                dfs(start, nxt, path, visited)
                path.pop()
                visited.discard(nxt)

    for s in nodes:
        dfs(s, s, [s], {s})
    return found

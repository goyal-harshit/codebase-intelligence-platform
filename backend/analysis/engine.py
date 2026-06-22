"""In-memory codebase analysis: structure, complexity, risks, dependencies.

Pure functions over the parser's (entities, relationships) output plus an
in-memory directed graph (networkx). No graph DB, vector DB, or LLM required.
"""
from __future__ import annotations

import math
import os
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from ._graph import DiGraph, descendants, simple_cycles

from ast_parser import parse_repository
from .git_insights import collect_git_insights

GOD_OBJECT_METHODS = 20
LONG_METHOD_LOC = 100
HIGH_COMPLEXITY = 15
SHOTGUN_FILES = 30
DEEP_INHERITANCE = 5

ENTRYPOINT_NAMES = {
    "main", "__init__", "__new__", "__call__", "__enter__", "__exit__",
    "setup", "teardown", "run", "handle", "dispatch", "wsgi_app", "asgi",
}


@dataclass
class CodebaseAnalysis:
    repo_path: str
    overview: dict = field(default_factory=dict)
    languages: dict = field(default_factory=dict)
    complexity: dict = field(default_factory=dict)
    maintainability: dict = field(default_factory=dict)
    risks: dict = field(default_factory=dict)
    dependencies: dict = field(default_factory=dict)
    call_graph: dict = field(default_factory=dict)
    documentation: dict = field(default_factory=dict)
    git: dict = field(default_factory=dict)
    hotspots: list = field(default_factory=list)
    health_score: dict = field(default_factory=dict)
    graph: dict = field(default_factory=dict)
    index: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "repo_path": self.repo_path,
            "overview": self.overview,
            "languages": self.languages,
            "complexity": self.complexity,
            "maintainability": self.maintainability,
            "risks": self.risks,
            "dependencies": self.dependencies,
            "call_graph": self.call_graph,
            "documentation": self.documentation,
            "git": self.git,
            "hotspots": self.hotspots,
            "health_score": self.health_score,
            "graph": self.graph,
        }


def _rel(path, root):
    try:
        return os.path.relpath(path, root)
    except ValueError:
        return path


def _module_of(rel_path):
    no_ext = os.path.splitext(rel_path)[0]
    parts = [p for p in no_ext.replace("\\", "/").split("/") if p and p != "."]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts) if parts else no_ext


def analyze_repository(repo_path, top_n=20, with_git=True):
    repo_path = os.path.abspath(repo_path)
    entities, relationships = parse_repository(repo_path)
    by_id = {e.id: e for e in entities}
    for e in entities:
        e.file_path = _rel(e.file_path, repo_path)
    a = CodebaseAnalysis(repo_path=repo_path)
    _overview(a, entities, repo_path)
    _languages(a, entities)
    _complexity(a, entities, top_n)
    _maintainability(a, entities, top_n)
    call_g, callers = _build_call_graph(entities, relationships, by_id)
    _call_graph_metrics(a, call_g, callers, by_id, top_n)
    _dependencies(a, entities, relationships, repo_path, top_n)
    _documentation(a, entities, top_n)
    _risks(a, entities, relationships, callers, by_id, top_n)
    if with_git:
        try:
            a.git = collect_git_insights(repo_path, top_n=top_n)
        except Exception as exc:
            a.git = {"available": False, "error": str(exc)}
    _hotspots(a, entities, top_n)
    _graph_view(a, entities, relationships, by_id, repo_path)
    _build_index(a, entities, relationships, by_id)
    _health_score(a)
    return a


def _overview(a, entities, repo_path):
    files = {e.file_path for e in entities}
    funcs = [e for e in entities if e.type in ("function", "method")]
    classes = [e for e in entities if e.type == "class"]
    loc = sum(_file_loc(os.path.join(repo_path, f)) for f in files)
    a.overview = {
        "files_analyzed": len(files),
        "total_entities": len(entities),
        "functions_and_methods": len(funcs),
        "classes": len(classes),
        "interfaces": len([e for e in entities if e.type == "interface"]),
        "total_lines_of_code": loc,
        "avg_entities_per_file": round(len(entities) / len(files), 1) if files else 0,
    }


def _file_loc(path):
    try:
        with open(path, "rb") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def _languages(a, entities):
    by_lang = Counter(e.language for e in entities)
    files_by_lang = defaultdict(set)
    for e in entities:
        files_by_lang[e.language].add(e.file_path)
    a.languages = {lang: {"entities": n, "files": len(files_by_lang[lang])}
                   for lang, n in by_lang.most_common()}


def _complexity(a, entities, top_n):
    funcs = [e for e in entities if e.type in ("function", "method")]
    cc = [e.cyclomatic_complexity for e in funcs] or [0]
    buckets = {"1-5 (simple)": 0, "6-10 (moderate)": 0,
               "11-20 (complex)": 0, "21+ (very complex)": 0}
    for v in cc:
        if v <= 5:
            buckets["1-5 (simple)"] += 1
        elif v <= 10:
            buckets["6-10 (moderate)"] += 1
        elif v <= 20:
            buckets["11-20 (complex)"] += 1
        else:
            buckets["21+ (very complex)"] += 1
    top = sorted(funcs, key=lambda e: e.cyclomatic_complexity, reverse=True)[:top_n]
    a.complexity = {
        "average": round(statistics.mean(cc), 2),
        "median": statistics.median(cc),
        "max": max(cc),
        "distribution": buckets,
        "most_complex": [{"name": e.name, "file": e.file_path, "line": e.line_start,
                          "complexity": e.cyclomatic_complexity, "loc": e.lines_of_code}
                         for e in top],
    }


def _maintainability(a, entities, top_n):
    per_file_cc = defaultdict(list)
    per_file_loc = defaultdict(int)
    for e in entities:
        if e.type in ("function", "method"):
            per_file_cc[e.file_path].append(e.cyclomatic_complexity)
            per_file_loc[e.file_path] += e.lines_of_code
    scores = []
    for f, ccs in per_file_cc.items():
        loc = max(per_file_loc[f], 1)
        avg_cc = statistics.mean(ccs)
        mi = 171 - 5.2 * math.log(loc + 1) - 0.23 * avg_cc - 16.2 * math.log(loc + 1)
        mi = max(0.0, min(100.0, mi * 100 / 171))
        scores.append({"file": f, "mi": round(mi, 1),
                       "avg_complexity": round(avg_cc, 1), "loc": loc})
    scores.sort(key=lambda s: s["mi"])
    grades = Counter()
    for s in scores:
        grades["A (>=85)" if s["mi"] >= 85 else
               "B (65-85)" if s["mi"] >= 65 else
               "C (<65, needs attention)"] += 1
    a.maintainability = {
        "average_index": round(statistics.mean([s["mi"] for s in scores]), 1) if scores else 0,
        "grade_distribution": dict(grades),
        "lowest_files": scores[:top_n],
    }


def _build_call_graph(entities, relationships, by_id):
    g = DiGraph()
    for e in entities:
        g.add_node(e.id)
    callers = defaultdict(set)
    for r in relationships:
        if r.type == "calls" and r.target_id in by_id and "external" not in r.metadata:
            if r.source_id in by_id and r.source_id != r.target_id:
                g.add_edge(r.source_id, r.target_id)
                callers[r.target_id].add(r.source_id)
    return g, callers


def _call_graph_metrics(a, g, callers, by_id, top_n):
    fan_in = {n: g.in_degree(n) for n in g.nodes}
    fan_out = {n: g.out_degree(n) for n in g.nodes}

    def info(eid):
        e = by_id[eid]
        return {"name": e.name, "file": e.file_path, "line": e.line_start}

    most_called = sorted(fan_in.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    most_calling = sorted(fan_out.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    rev = g.reverse(copy=False)
    blast = []
    for eid, _ in most_called[:top_n]:
        if fan_in[eid] == 0:
            continue
        affected = descendants(rev, eid)
        blast.append({**info(eid), "directly_affected": fan_in[eid],
                      "transitively_affected": len(affected)})
    blast.sort(key=lambda b: b["transitively_affected"], reverse=True)
    a.call_graph = {
        "edges": g.number_of_edges(),
        "most_called_functions": [{**info(eid), "called_by": d}
                                  for eid, d in most_called if d > 0],
        "highest_fan_out": [{**info(eid), "calls_out": d}
                            for eid, d in most_calling if d > 0],
        "blast_radius_top": blast[:top_n],
    }


def _dependencies(a, entities, relationships, repo_path, top_n):
    files = {e.file_path for e in entities}
    file_to_module = {f: _module_of(f) for f in files}
    internal_modules = set(file_to_module.values())
    mod_graph = DiGraph()
    mod_graph.add_nodes_from(internal_modules)
    external = Counter()
    ext_by_file = defaultdict(set)
    for r in relationships:
        if r.type != "imports":
            continue
        src_file = _rel(r.source_id, repo_path)
        src_mod = file_to_module.get(src_file)
        target = r.target_id
        matched = None
        for m in internal_modules:
            if m == target or m.endswith("." + target) or m.split(".")[-1] == target:
                matched = m
                break
        if matched and src_mod and matched != src_mod:
            mod_graph.add_edge(src_mod, matched)
        elif not matched:
            external[target] += 1
            ext_by_file[src_file].add(target)
    cycles = []
    try:
        for cyc in simple_cycles(mod_graph):
            if len(cyc) >= 2:
                cycles.append(cyc)
    except Exception:
        pass
    in_deg = sorted(mod_graph.in_degree, key=lambda kv: kv[1], reverse=True)
    out_deg = sorted(mod_graph.out_degree, key=lambda kv: kv[1], reverse=True)
    a.dependencies = {
        "internal_modules": len(internal_modules),
        "internal_dependency_edges": mod_graph.number_of_edges(),
        "external_dependencies": len(external),
        "circular_dependencies": cycles[:top_n],
        "circular_dependency_count": len(cycles),
        "most_depended_on": [{"module": m, "depended_on_by": d}
                             for m, d in in_deg[:top_n] if d > 0],
        "most_dependencies": [{"module": m, "imports": d}
                              for m, d in out_deg[:top_n] if d > 0],
        "top_external": [{"package": p, "import_sites": c}
                         for p, c in external.most_common(top_n)],
        "dependency_heavy_files": sorted(
            ({"file": f, "external_imports": len(s)} for f, s in ext_by_file.items()),
            key=lambda x: x["external_imports"], reverse=True)[:top_n],
    }


def _documentation(a, entities, top_n):
    py_funcs = [e for e in entities
                if e.language == "python" and e.type in ("function", "method")]
    documented = [e for e in py_funcs if e.docstring]
    undoc = sorted([e for e in py_funcs if not e.docstring and e.cyclomatic_complexity >= 5],
                   key=lambda e: e.cyclomatic_complexity, reverse=True)[:top_n]
    a.documentation = {
        "python_functions": len(py_funcs),
        "documented": len(documented),
        "coverage_pct": round(100 * len(documented) / len(py_funcs), 1) if py_funcs else None,
        "undocumented_complex": [{"name": e.name, "file": e.file_path, "line": e.line_start,
                                  "complexity": e.cyclomatic_complexity} for e in undoc],
    }


def _risks(a, entities, relationships, callers, by_id, top_n):
    methods_per_class = defaultdict(int)
    for r in relationships:
        if r.type == "contains" and r.source_id in by_id:
            if by_id[r.source_id].type == "class":
                methods_per_class[r.source_id] += 1
    god = [{"name": by_id[cid].name, "file": by_id[cid].file_path,
            "line": by_id[cid].line_start, "methods": n}
           for cid, n in methods_per_class.items() if n > GOD_OBJECT_METHODS]
    god.sort(key=lambda x: x["methods"], reverse=True)

    dead_private, dead_public = [], []
    for e in entities:
        if e.type not in ("function", "method"):
            continue
        if callers.get(e.id):
            continue
        if e.name in ENTRYPOINT_NAMES or e.name.startswith("test_"):
            continue
        if "test" in e.file_path.lower():
            continue
        if e.name.startswith("__") and e.name.endswith("__"):
            continue
        row = {"name": e.name, "file": e.file_path, "line": e.line_start, "loc": e.lines_of_code}
        (dead_private if e.name.startswith("_") else dead_public).append(row)
    dead_private.sort(key=lambda x: x["loc"], reverse=True)
    dead_public.sort(key=lambda x: x["loc"], reverse=True)

    long_methods = sorted(
        [{"name": e.name, "file": e.file_path, "line": e.line_start, "loc": e.lines_of_code}
         for e in entities if e.type in ("function", "method") and e.lines_of_code > LONG_METHOD_LOC],
        key=lambda x: x["loc"], reverse=True)
    high_cc = sorted(
        [{"name": e.name, "file": e.file_path, "line": e.line_start, "complexity": e.cyclomatic_complexity}
         for e in entities if e.type in ("function", "method") and e.cyclomatic_complexity > HIGH_COMPLEXITY],
        key=lambda x: x["complexity"], reverse=True)

    shotgun = []
    for tid, caller_ids in callers.items():
        cfiles = {by_id[c].file_path for c in caller_ids if c in by_id}
        if len(cfiles) > SHOTGUN_FILES:
            e = by_id[tid]
            shotgun.append({"name": e.name, "file": e.file_path,
                            "line": e.line_start, "called_from_files": len(cfiles)})
    shotgun.sort(key=lambda x: x["called_from_files"], reverse=True)

    inh = DiGraph()
    for r in relationships:
        if r.type == "inherits_from" and r.target_id in by_id and r.source_id in by_id:
            inh.add_edge(r.source_id, r.target_id)
    deep = []
    for n in inh.nodes:
        if inh.in_degree(n) == 0:
            try:
                depth = max((len(p) - 1 for p in _all_paths_to_roots(inh, n)), default=0)
            except Exception:
                depth = 0
            if depth >= DEEP_INHERITANCE:
                e = by_id[n]
                deep.append({"name": e.name, "file": e.file_path, "depth": depth})
    deep.sort(key=lambda x: x["depth"], reverse=True)

    a.risks = {
        "god_objects": god[:top_n],
        "dead_code": {"count": len(dead_private), "items": dead_private[:top_n],
                      "unused_public_api": len(dead_public), "public_items": dead_public[:top_n]},
        "long_methods": long_methods[:top_n],
        "high_complexity": high_cc[:top_n],
        "shotgun_surgery": shotgun[:top_n],
        "deep_inheritance": deep[:top_n],
        "summary": {
            "god_objects": len(god),
            "dead_code": len(dead_private),
            "unused_public_api": len(dead_public),
            "long_methods": len(long_methods),
            "high_complexity": len(high_cc),
            "shotgun_surgery": len(shotgun),
            "deep_inheritance": len(deep),
        },
    }


def _all_paths_to_roots(g, node, _seen=None):
    _seen = _seen or set()
    if node in _seen:
        return [[node]]
    _seen = _seen | {node}
    succ = list(g.successors(node))
    if not succ:
        return [[node]]
    paths = []
    for s in succ:
        for p in _all_paths_to_roots(g, s, _seen):
            paths.append([node] + p)
    return paths


def _hotspots(a, entities, top_n):
    churn = {}
    for item in (a.git or {}).get("file_churn", []):
        churn[item["file"]] = item["commits"]
    per_file_cc = defaultdict(int)
    for e in entities:
        if e.type in ("function", "method"):
            per_file_cc[e.file_path] = max(per_file_cc[e.file_path], e.cyclomatic_complexity)
    rows = []
    for f, max_cc in per_file_cc.items():
        c = churn.get(f, 0)
        score = max_cc * c if churn else max_cc
        rows.append({"file": f, "max_complexity": max_cc, "commits": c, "hotspot_score": score})
    rows.sort(key=lambda r: r["hotspot_score"], reverse=True)
    a.hotspots = rows[:top_n]


def _health_score(a):
    risks = a.risks.get("summary", {})
    n_funcs = max(a.overview.get("functions_and_methods", 1), 1)
    maint = a.maintainability.get("average_index", 50)
    doc = a.documentation.get("coverage_pct")
    doc = doc if doc is not None else 60
    complexity_penalty = min(40, 100 * risks.get("high_complexity", 0) / n_funcs * 4)
    deadcode_penalty = min(25, 100 * risks.get("dead_code", 0) / n_funcs)
    circ = a.dependencies.get("circular_dependency_count", 0)
    circ_penalty = min(15, circ * 3)
    structure = max(0, 100 - complexity_penalty - deadcode_penalty - circ_penalty)
    overall = round(0.4 * maint + 0.25 * structure + 0.2 * doc +
                    0.15 * (100 - min(100, circ * 5)), 1)
    a.health_score = {
        "overall": overall,
        "grade": ("A" if overall >= 85 else "B" if overall >= 70 else
                  "C" if overall >= 55 else "D" if overall >= 40 else "F"),
        "components": {"maintainability": round(maint, 1),
                       "structure": round(structure, 1),
                       "documentation": round(doc, 1)},
    }


def _graph_view(a, entities, relationships, by_id, repo_path, max_nodes=160):
    """File-level dependency graph (nodes=files, edges=imports + cross-file
    calls) for interactive visualization."""
    files = sorted({e.file_path for e in entities})
    file_index = {f: _module_of(f) for f in files}
    # per-file stats
    loc = defaultdict(int)
    ent_count = defaultdict(int)
    max_cc = defaultdict(int)
    for e in entities:
        ent_count[e.file_path] += 1
        if e.type in ("function", "method"):
            loc[e.file_path] += e.lines_of_code
            max_cc[e.file_path] = max(max_cc[e.file_path], e.cyclomatic_complexity)

    # entity id -> file
    eid_file = {e.id: e.file_path for e in entities}
    edges = defaultdict(lambda: {"call": 0, "import": 0})

    # cross-file call edges
    for r in relationships:
        if r.type == "calls" and r.source_id in eid_file and r.target_id in eid_file:
            sf, tf = eid_file[r.source_id], eid_file[r.target_id]
            if sf != tf:
                edges[(sf, tf)]["call"] += 1

    # import edges (file -> internal file whose module matches)
    mod_to_file = {}
    for f in files:
        mod_to_file.setdefault(file_index[f], f)
    for r in relationships:
        if r.type != "imports":
            continue
        sf = _rel(r.source_id, repo_path)
        if sf not in file_index:
            continue
        target = r.target_id
        match_file = None
        for m, mf in mod_to_file.items():
            if m == target or m.endswith("." + target) or m.split(".")[-1] == target:
                match_file = mf
                break
        if match_file and match_file != sf:
            edges[(sf, match_file)]["import"] += 1

    # degree for ranking
    deg = defaultdict(int)
    for (sf, tf), w in edges.items():
        deg[sf] += 1
        deg[tf] += 1
    ranked = sorted(files, key=lambda f: (deg[f], ent_count[f]), reverse=True)[:max_nodes]
    keep = set(ranked)

    def short(f):
        return f.replace("\\", "/").split("/")[-1]

    def group(f):
        parts = f.replace("\\", "/").split("/")
        return parts[0] if len(parts) > 1 else "(root)"

    nodes = [{
        "id": f, "label": short(f), "group": group(f),
        "entities": ent_count[f], "loc": loc[f],
        "max_complexity": max_cc[f], "degree": deg[f],
    } for f in ranked]

    links = []
    for (sf, tf), w in edges.items():
        if sf in keep and tf in keep:
            links.append({"source": sf, "target": tf,
                          "type": "import" if w["import"] >= w["call"] else "call",
                          "weight": w["call"] + w["import"]})

    a.graph = {"nodes": nodes, "links": links,
               "node_count": len(nodes), "link_count": len(links),
               "truncated": len(files) > max_nodes}


def _label_propagation(nodes, adj, rounds=8):
    """Simple community detection (synchronous-ish label propagation)."""
    label = {n: i for i, n in enumerate(nodes)}
    import random
    rnd = random.Random(42)
    order = list(nodes)
    for _ in range(rounds):
        rnd.shuffle(order)
        changed = False
        for n in order:
            nbrs = adj.get(n)
            if not nbrs:
                continue
            counts = Counter(label[x] for x in nbrs)
            best = max(counts.items(), key=lambda kv: (kv[1], -kv[0]))[0]
            if label[n] != best:
                label[n] = best
                changed = True
        if not changed:
            break
    return label


def _build_index(a, entities, relationships, by_id):
    """Rich per-entity index + adjacency + file grouping + communities +
    god nodes + suggested questions. Powers the Functions explorer and Q&A."""
    callees = defaultdict(list)
    callers = defaultdict(list)
    for r in relationships:
        if r.type == "calls" and r.source_id in by_id and r.target_id in by_id                 and "external" not in r.metadata and r.source_id != r.target_id:
            callees[r.source_id].append(r.target_id)
            callers[r.target_id].append(r.source_id)

    contains = defaultdict(list)  # class id -> child ids
    parent_of = {}
    for r in relationships:
        if r.type == "contains" and r.source_id in by_id and r.target_id in by_id:
            contains[r.source_id].append(r.target_id)
            parent_of[r.target_id] = r.source_id

    ents = {}
    files = defaultdict(list)
    for e in entities:
        ents[e.id] = {
            "id": e.id, "name": e.name, "type": e.type, "file": e.file_path,
            "line": e.line_start, "line_end": e.line_end, "signature": e.signature,
            "docstring": e.docstring, "complexity": e.cyclomatic_complexity,
            "loc": e.lines_of_code, "language": e.language,
            "callers": sorted(set(callers.get(e.id, []))),
            "callees": sorted(set(callees.get(e.id, []))),
            "parent": parent_of.get(e.id),
            "children": contains.get(e.id, []),
        }
        files[e.file_path].append(e.id)

    # communities = directory groups (intuitive + always color-distinct).
    # Use up to the first two path segments so big trees stay readable.
    def _ckey(f):
        parts = f.replace("\\", "/").split("/")[:-1]
        if not parts:
            return "(root)"
        return "/".join(parts[:2])

    gnodes = [n["id"] for n in a.graph.get("nodes", [])]
    key_to_id = {}
    labels = {}
    for f in gnodes:
        k = _ckey(f)
        if k not in key_to_id:
            key_to_id[k] = len(key_to_id)
        labels[f] = key_to_id[k]
    comm_files = defaultdict(list)
    for f, c in labels.items():
        comm_files[c].append(f)
    id_to_key = {v: k for k, v in key_to_id.items()}
    # name each community by most common top-level folder
    communities = []
    deg = {n["id"]: n["degree"] for n in a.graph.get("nodes", [])}
    for c, fl in comm_files.items():
        folder = id_to_key.get(c, "(root)")
        hub = max(fl, key=lambda f: deg.get(f, 0))
        communities.append({
            "id": c, "name": folder, "files": sorted(fl), "size": len(fl),
            "hub_file": hub,
            "entities": sum(len(files.get(f, [])) for f in fl),
        })
    communities.sort(key=lambda x: x["size"], reverse=True)
    file_comm = {f: c for c, fl in comm_files.items() for f in fl}
    for n in a.graph.get("nodes", []):
        n["community"] = file_comm.get(n["id"], -1)

    # god nodes: most-connected files + most-called functions
    god_files = sorted(a.graph.get("nodes", []), key=lambda n: n["degree"], reverse=True)[:10]
    god_funcs = sorted(
        (ents[e] for e in ents if ents[e]["type"] in ("function", "method")),
        key=lambda e: len(e["callers"]), reverse=True)[:10]

    # suggested onboarding questions, grounded in the data
    sq = []
    if god_funcs and god_funcs[0]["callers"]:
        sq.append("What does %s do?" % god_funcs[0]["name"])
        sq.append("Who calls %s?" % god_funcs[0]["name"])
    if a.complexity.get("most_complex"):
        sq.append("Explain %s" % a.complexity["most_complex"][0]["name"])
    if god_files:
        sq.append("What is in %s?" % god_files[0]["id"])
    if communities:
        sq.append("What is the %s module for?" % communities[0]["name"])
    sq.append("Where is the entry point?")

    a.index = {
        "entities": ents,
        "files": {f: ids for f, ids in files.items()},
        "communities": communities,
        "god_files": [{"file": n["id"], "degree": n["degree"],
                       "entities": n.get("entities", 0)} for n in god_files],
        "god_functions": [{"id": e["id"], "name": e["name"], "file": e["file"],
                           "callers": len(e["callers"])} for e in god_funcs],
        "suggested_questions": sq[:6],
        "entity_count": len(ents),
    }

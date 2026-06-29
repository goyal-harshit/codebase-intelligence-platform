import json
from graphify.analyze import graph_diff
from graphify.build import build_from_json
from networkx.readwrite import json_graph
import networkx as nx
from pathlib import Path

# Load old graph (before update) from backup
old_data = json.loads(Path("graphify-out/.graphify_old.json").read_text(encoding="utf-8")) if Path("graphify-out/.graphify_old.json").exists() else None
new_extract = json.loads(Path("graphify-out/.graphify_extract.json").read_text(encoding="utf-8")) if Path("graphify-out/.graphify_extract.json").exists() else None

if old_data and new_extract:
    G_old = json_graph.node_link_graph(old_data, edges="links")
    G_new = build_from_json(new_extract, directed=False) if new_extract else None
    
    if G_new:
        diff = graph_diff(G_old, G_new)
        print(diff["summary"])
        if diff["new_nodes"]:
            print("New nodes: " + ", ".join(n["label"] for n in diff["new_nodes"][:5]))
        if diff["new_edges"]:
            print("New edges: " + str(len(diff["new_edges"])))
else:
    print("[graphify update] No diff available (old graph not found)")
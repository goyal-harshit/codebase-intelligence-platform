import json
from pathlib import Path
from graphify.build import build_merge
from graphify.detect import save_manifest

# Load new extraction and incremental state
new_extraction = json.loads(Path("graphify-out/.graphify_extract.json").read_text(encoding="utf-8"))
incremental = json.loads(Path("graphify-out/.graphify_incremental.json").read_text(encoding="utf-8"))
deleted = list(incremental.get("deleted_files", []))

# Prune only genuinely deleted files
prune = list(deleted) or None

# Merge with existing graph
G = build_merge(
    [new_extraction],
    graph_path="graphify-out/graph.json",
    prune_sources=prune,
    root=".",
    directed=False,
)
msg1 = "[graphify update] Merged: " + str(G.number_of_nodes()) + " nodes, " + str(G.number_of_edges()) + " edges"
print(msg1)

# Write merged result back for Step 4
merged_out = {
    "nodes": [{"id": n, **d} for n, d in G.nodes(data=True)],
    "edges": [
        {**{k: val for k, val in d.items() if k not in ("_src", "_tgt", "source", "target")},
         "source": d.get("_src", u), "target": d.get("_tgt", v)}
        for u, v, d in G.edges(data=True)
    ],
    "hyperedges": list(G.graph.get("hyperedges", [])),
    "input_tokens": new_extraction.get("input_tokens", 0),
    "output_tokens": new_extraction.get("output_tokens", 0),
}
Path("graphify-out/.graphify_extract.json").write_text(json.dumps(merged_out, ensure_ascii=False), encoding="utf-8")
n_nodes = len(merged_out["nodes"])
n_edges = len(merged_out["edges"])
msg2 = "[graphify update] Extraction updated (" + str(n_nodes) + " nodes, " + str(n_edges) + " edges)"
print(msg2)

# Save manifest for next --update
save_manifest(incremental["files"], root=".")
print("[graphify update] Manifest saved.")
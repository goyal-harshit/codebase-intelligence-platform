import json
from pathlib import Path
from graphify.build import build_from_json
from graphify.cluster import score_all
from graphify.analyze import god_nodes, surprising_connections, suggest_questions
from graphify.report import generate

extraction = json.loads(Path("graphify-out/.graphify_extract.json").read_text(encoding="utf-8"))
detection  = json.loads(Path("graphify-out/.graphify_detect.json").read_text(encoding="utf-8"))
analysis   = json.loads(Path("graphify-out/.graphify_analysis.json").read_text(encoding="utf-8"))

# Rebuild graph
G = build_from_json(extraction, root=".", directed=False)
communities = {int(k): v for k, v in analysis["communities"].items()}
cohesion = {int(k): v for k, v in analysis["cohesion"].items()}
tokens = {"input": extraction.get("input_tokens", 0), "output": extraction.get("output_tokens", 0)}

# Auto-label communities based on their content
labels = {}
for cid, node_ids in communities.items():
    # Sample first few nodes in community to infer a name
    sample_names = []
    for nid in list(node_ids)[:5]:
        if nid in G.nodes:
            label = G.nodes[nid].get("label", nid)
            if label:
                sample_names.append(label.split("::")[0][:20])
    if sample_names:
        labels[cid] = " · ".join(set(sample_names))[:40]
    else:
        labels[cid] = "Community " + str(cid)

# Regenerate questions with real labels
questions = suggest_questions(G, communities, labels)

# Regenerate report
report = generate(G, communities, cohesion, labels, analysis["gods"], analysis["surprises"], detection, tokens, ".", suggested_questions=questions)
Path("graphify-out/GRAPH_REPORT.md").write_text(report, encoding="utf-8")
Path("graphify-out/.graphify_labels.json").write_text(json.dumps({str(k): v for k, v in labels.items()}, ensure_ascii=False), encoding="utf-8")

print("[graphify] Report updated with community labels")
print("[graphify] " + str(len(labels)) + " communities labeled")
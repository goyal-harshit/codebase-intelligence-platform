# Analysis Engine (offline, zero-services)

Computes a complete codebase intelligence report **without** ArcadeDB, ChromaDB,
Ollama, or Docker. It runs the AST parser, builds an in-memory graph (networkx),
and derives every insight, plus git-history insights when a `.git` is present.

```bash
python scripts/analyze.py <repo_path> --out reports --name <label>
# -> reports/<label>_report.html  and  reports/<label>_report.json
```

## Insights produced

| Section | What it answers |
|---|---|
| Health score | Single 0–100 grade (maintainability + structure + docs) |
| Overview | Files, LOC, functions, classes, languages |
| Complexity | Distribution, most complex functions, median/max |
| Maintainability | Per-file Maintainability Index, worst files |
| Architecture risks | God objects, dead code (private vs public-API), long methods, high complexity, shotgun surgery, deep inheritance |
| Dependencies | Internal module graph, circular deps, most depended-on, top external packages |
| Call graph & impact | Critical hubs (fan-in), blast radius (transitive change impact) |
| Documentation | Docstring coverage, complex-but-undocumented functions |
| Version control | Commits, contributors, bus factor, churn, single-owner knowledge-risk files |
| Hotspots | complexity × churn — where to refactor first |

Dead-code detection is split by confidence: unused **private** symbols are
high-confidence; unused **public** symbols are reported separately as likely
external API / entry points (avoids the library false-positive problem).

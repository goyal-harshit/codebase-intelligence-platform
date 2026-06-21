# Enterprise Codebase Intelligence Platform — Master Implementation Plan
### Full-Detail Build Guide: What to Build, How, From Where, and What to Expect

---

# PART 0 — PROJECT CHARTER

## 0.1 What You Are Building
An open-source platform that:
1. Ingests any Git repository (any size, any mix of languages)
2. Parses every file into an Abstract Syntax Tree (AST)
3. Converts the AST into a **knowledge graph** (functions, classes, files, modules, dependencies, calls, inheritance)
4. Stores semantic embeddings of every code unit in a **vector database**
5. Lets a user ask plain-English questions ("What breaks if I change `auth.py`?") and get accurate, cited answers
6. Automatically detects architectural risks (circular dependencies, god objects, dead code, security smells)
7. Computes **change-impact / blast-radius** analysis for any file or function
8. Tracks code ownership (via `git blame`) and test coverage
9. Exposes all of this through a REST API and a web dashboard

## 0.2 Definition of Done (v1.0)
- Can ingest a 50,000-line, 3-language repo in under 60 seconds (initial) and under 5 seconds (incremental)
- Can answer 80%+ of structural questions correctly ("who calls X", "what does X depend on")
- Can answer 70%+ of semantic questions correctly ("where is auth handled")
- Detects at least 5 categories of architecture risk with <20% false-positive rate
- Has a working web UI: dashboard, search/query box, graph visualizer, risk list
- Fully Dockerized, one-command (`docker compose up`) local deployment
- Zero paid services required to run the entire stack

## 0.3 Who This Is For
- Engineering teams onboarding new hires onto large codebases
- Tech leads doing architecture reviews
- Open-source maintainers wanting automated PR impact analysis
- You — as a portfolio-defining, resume-grade systems project

## 0.4 Non-Goals (v1.0)
- Not a CI/CD security scanner replacement (Snyk/Semgrep do this better — you can integrate them later)
- Not a code-generation/autocomplete tool
- Not a distributed, billion-node graph system (that's a v2+ goal)

---

# PART 1 — COMPLETE TECHNOLOGY STACK (with exact sources)

| Layer | Tool | License | Official Source | Why |
|---|---|---|---|---|
| AST Parsing | **Tree-sitter** | MIT | https://tree-sitter.github.io/tree-sitter/ | Language-agnostic, incremental, 1000+ files/sec |
| AST Parsing (Python alt) | `ast` (stdlib) | PSF | https://docs.python.org/3/library/ast.html | Zero install, native Python parsing |
| Graph Database | **ArcadeDB** | Apache 2.0 | https://arcadedb.com / https://github.com/ArcadeData/arcadedb | No license traps, Cypher-compatible, multi-model |
| Graph Database (alt) | Neo4j Community | GPLv3 | https://neo4j.com/download-center/#community | More mature tooling, single-instance only |
| Vector Database | **ChromaDB** | Apache 2.0 | https://www.trychroma.com / https://github.com/chroma-core/chroma | 5-minute setup, good for <10M vectors |
| Embedding Model | **BAAI/bge-small-en-v1.5** | MIT | https://huggingface.co/BAAI/bge-small-en-v1.5 | 384-dim, fast, strong retrieval benchmarks |
| LLM Runtime | **Ollama** | MIT | https://ollama.com | Local LLM serving, zero API cost |
| LLM Model | **Mistral 7B** | Apache 2.0 | https://ollama.com/library/mistral | Best speed/quality ratio for Cypher gen + reasoning |
| LLM Model (code-heavy) | **CodeLlama 13B** | Llama license | https://ollama.com/library/codellama | Specialized for code understanding |
| Backend Framework | **FastAPI** | MIT | https://fastapi.tiangolo.com | Async, auto-generated OpenAPI docs |
| Task Queue | **Celery** | BSD | https://docs.celeryq.dev | Mature distributed task processing |
| Message Broker | **Redis** | BSD/RSALv2 (use 7.x BSD) | https://redis.io | Celery broker + caching |
| Frontend Framework | **Next.js 14** | MIT | https://nextjs.org | Full-stack React, file-based routing |
| Styling | **TailwindCSS** | MIT | https://tailwindcss.com | Utility-first CSS, fast iteration |
| Graph Visualization | **D3.js** or **react-force-graph** | ISC/MIT | https://d3js.org / https://github.com/vasturiano/react-force-graph | Interactive node-link diagrams |
| Charts | **Recharts** | MIT | https://recharts.org | Dashboards, stat charts |
| Containerization | **Docker + Docker Compose** | Apache 2.0 | https://docker.com | One-command deployment |
| Version Control Analysis | **GitPython** | BSD | https://gitpython.readthedocs.io | Programmatic git blame/log access |
| Monitoring | **Prometheus + Grafana** | Apache 2.0 | https://prometheus.io / https://grafana.com | Free observability stack |
| Testing | **pytest** + **Jest** | MIT | https://pytest.org / https://jestjs.io | Python backend + JS frontend testing |
| CI/CD | **GitHub Actions** | Free for public repos | https://github.com/features/actions | Free unlimited minutes for OSS |

### 1.1 Installation Commands (Run These First, In Order)

```bash
# 1. Docker (required for everything)
# Linux:
curl -fsSL https://get.docker.com | sh
# macOS/Windows: download Docker Desktop from docker.com

# 2. Python 3.11+ environment
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install --upgrade pip

# 3. Node.js 20+ (for frontend) — use nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
nvm install 20
nvm use 20

# 4. Ollama (local LLM)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull mistral
ollama pull codellama:13b   # optional, needs ~8GB RAM free

# 5. Tree-sitter CLI (optional, for grammar testing)
npm install -g tree-sitter-cli

# 6. Git (you probably have this)
git --version
```

---

# PART 2 — SYSTEM ARCHITECTURE (Data Flow)

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  Git Repo   │────▶│ Tree-sitter  │────▶│  Entity/Edge   │
│ (any lang)  │     │   Parser     │     │   Extractor    │
└─────────────┘     └──────────────┘     └───────┬────────┘
                                                   │
                  ┌────────────────────────────────┴────────────────────────────┐
                  ▼                                                              ▼
         ┌─────────────────┐                                         ┌──────────────────┐
         │   ArcadeDB        │                                       │   ChromaDB         │
         │ (Graph: nodes,    │                                       │ (Vector: code      │
         │  edges, metadata) │                                       │  embeddings)        │
         └────────┬──────────┘                                       └─────────┬──────────┘
                  │                                                              │
                  └─────────────────────┬────────────────────────────────────────┘
                                         ▼
                              ┌────────────────────┐
                              │  Hybrid Retriever    │
                              │ (structural+semantic)│
                              └──────────┬───────────┘
                                         ▼
                              ┌────────────────────┐
                              │  Ollama (Mistral)    │
                              │  Answer Generation    │
                              └──────────┬───────────┘
                                         ▼
                              ┌────────────────────┐
                              │   FastAPI Backend    │
                              └──────────┬───────────┘
                                         ▼
                              ┌────────────────────┐
                              │  Next.js Frontend    │
                              │ (Dashboard, Query UI) │
                              └────────────────────┘
```

---

# PART 3 — DAY 1: PROJECT SETUP (Do This First)

### Step-by-step (expect ~3-4 hours)

1. **Create the GitHub repo**
   ```bash
   mkdir enterprise-codebase-intelligence && cd enterprise-codebase-intelligence
   git init
   gh repo create enterprise-codebase-intelligence --public --source=. # requires GitHub CLI
   ```

2. **Create folder skeleton**
   ```bash
   mkdir -p backend/{ast_parser,graph_db,vector_db,retrieval,llm,risk_detection,api,tests}
   mkdir -p frontend/{pages,components,lib,styles}
   mkdir -p infra docs scripts
   touch README.md LICENSE .gitignore docker-compose.yml
   ```

3. **Choose license**: Apache 2.0 (matches your stack, protects you legally)
   - Source: https://choosealicense.com/licenses/apache-2.0/
   - Generate with: `gh repo create` prompt, or copy from https://www.apache.org/licenses/LICENSE-2.0.txt

4. **Write `.gitignore`** (Python + Node + Docker)
   ```
   venv/
   __pycache__/
   *.pyc
   node_modules/
   .next/
   .env
   data/
   *.log
   ```

5. **Set up pre-commit hooks** (code quality from day 1)
   ```bash
   pip install pre-commit black isort flake8
   ```
   `.pre-commit-config.yaml`:
   ```yaml
   repos:
     - repo: https://github.com/psf/black
       rev: 24.1.1
       hooks: [{id: black}]
     - repo: https://github.com/pycqa/isort
       rev: 5.13.2
       hooks: [{id: isort}]
   ```
   ```bash
   pre-commit install
   ```

**Acceptance criteria for Day 1:** repo exists on GitHub, has README, LICENSE, folder skeleton committed, pre-commit hook runs on `git commit`.

---

# PART 4 — PHASE 1: AST PARSING ENGINE (Weeks 1-2)

## 4.1 What You're Building
A module that takes any source file and outputs a structured list of `CodeEntity` and `CodeRelationship` objects — language-agnostic.

## 4.2 Exact Setup

```bash
pip install tree-sitter tree-sitter-languages
```
`tree-sitter-languages` (https://github.com/grantjenks/py-tree-sitter-languages) ships **pre-built binaries for 40+ languages** — this saves you from compiling grammars yourself.

## 4.3 Core Parser Module — `backend/ast_parser/parser.py`

```python
from tree_sitter_languages import get_language, get_parser
from dataclasses import dataclass, field
from typing import Optional
import hashlib

@dataclass
class CodeEntity:
    id: str
    type: str            # "function", "class", "method", "module"
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
    type: str             # "calls", "imports", "inherits", "references"
    metadata: dict = field(default_factory=dict)

# Map file extensions to tree-sitter language names
LANGUAGE_MAP = {
    ".py": "python", ".js": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "tsx", ".go": "go",
    ".rs": "rust", ".java": "java", ".rb": "ruby",
    ".php": "php", ".c": "c", ".cpp": "cpp", ".cs": "c_sharp",
}

# Node types per language that represent "entities" we care about
ENTITY_NODE_TYPES = {
    "python": {"function_definition": "function", "class_definition": "class"},
    "javascript": {"function_declaration": "function", "class_declaration": "class",
                   "method_definition": "method", "arrow_function": "function"},
    "typescript": {"function_declaration": "function", "class_declaration": "class",
                   "interface_declaration": "interface"},
    "go": {"function_declaration": "function", "method_declaration": "method"},
    "rust": {"function_item": "function", "struct_item": "class", "impl_item": "implementation"},
    "java": {"method_declaration": "method", "class_declaration": "class"},
}

class UniversalParser:
    def __init__(self):
        self._parser_cache = {}

    def _get_parser(self, language: str):
        if language not in self._parser_cache:
            self._parser_cache[language] = get_parser(language)
        return self._parser_cache[language]

    def detect_language(self, file_path: str) -> Optional[str]:
        import os
        ext = os.path.splitext(file_path)[1]
        return LANGUAGE_MAP.get(ext)

    def parse_file(self, file_path: str) -> tuple[list[CodeEntity], list[CodeRelationship]]:
        language = self.detect_language(file_path)
        if not language:
            return [], []

        with open(file_path, "rb") as f:
            source_code = f.read()

        parser = self._get_parser(language)
        tree = parser.parse(source_code)
        entities = []
        relationships = []

        entity_types = ENTITY_NODE_TYPES.get(language, {})
        self._walk_tree(tree.root_node, source_code, file_path, language,
                         entity_types, entities, relationships, parent_id=None)

        return entities, relationships

    def _walk_tree(self, node, source_code, file_path, language,
                    entity_types, entities, relationships, parent_id):
        node_type = node.type

        if node_type in entity_types:
            name_node = node.child_by_field_name("name")
            name = self._get_text(name_node, source_code) if name_node else "anonymous"
            entity_id = self._make_id(file_path, name, node.start_point[0])

            entity = CodeEntity(
                id=entity_id,
                type=entity_types[node_type],
                name=name,
                file_path=file_path,
                language=language,
                line_start=node.start_point[0] + 1,
                line_end=node.end_point[0] + 1,
                lines_of_code=node.end_point[0] - node.start_point[0] + 1,
                cyclomatic_complexity=self._compute_complexity(node),
                raw_code=self._get_text(node, source_code)[:2000],  # cap for storage
            )
            entities.append(entity)

            if parent_id:
                relationships.append(CodeRelationship(
                    source_id=parent_id, target_id=entity_id, type="contains"
                ))
            parent_id = entity_id

        # Detect function calls
        if node_type == "call" or node_type == "call_expression":
            callee = self._extract_call_target(node, source_code)
            if callee and parent_id:
                relationships.append(CodeRelationship(
                    source_id=parent_id,
                    target_id=callee,  # resolved later in symbol resolution pass
                    type="calls",
                    metadata={"unresolved_name": callee}
                ))

        for child in node.children:
            self._walk_tree(child, source_code, file_path, language,
                             entity_types, entities, relationships, parent_id)

    def _get_text(self, node, source_code) -> str:
        return source_code[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

    def _make_id(self, file_path: str, name: str, line: int) -> str:
        raw = f"{file_path}:{name}:{line}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _extract_call_target(self, node, source_code) -> Optional[str]:
        fn_node = node.child_by_field_name("function")
        if fn_node:
            return self._get_text(fn_node, source_code)
        return None

    def _compute_complexity(self, node) -> int:
        """Cyclomatic complexity: count branching nodes + 1"""
        BRANCH_TYPES = {"if_statement", "for_statement", "while_statement",
                         "case_clause", "catch_clause", "conditional_expression"}
        count = 1
        def visit(n):
            nonlocal count
            if n.type in BRANCH_TYPES:
                count += 1
            for c in n.children:
                visit(c)
        visit(node)
        return count
```

## 4.4 Repository Walker — `backend/ast_parser/repo_walker.py`

```python
import os
import hashlib

IGNORE_DIRS = {".git", "node_modules", "venv", "__pycache__", "dist", "build", ".next"}

def walk_repository(repo_path: str):
    """Yields file paths for all parseable source files"""
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for file in files:
            yield os.path.join(root, file)

def file_hash(file_path: str) -> str:
    """SHA-256 of file content — used for incremental update detection"""
    with open(file_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()
```

## 4.5 Symbol Resolution Pass (resolves `calls` edges to real entity IDs)

```python
class SymbolResolver:
    def resolve(self, entities: list[CodeEntity], relationships: list[CodeRelationship]):
        """Second pass: match unresolved call names to actual entity IDs"""
        name_index = {}
        for e in entities:
            name_index.setdefault(e.name, []).append(e.id)

        resolved = []
        for rel in relationships:
            if rel.type == "calls" and "unresolved_name" in rel.metadata:
                name = rel.metadata["unresolved_name"]
                candidates = name_index.get(name, [])
                if len(candidates) == 1:
                    rel.target_id = candidates[0]
                    resolved.append(rel)
                elif len(candidates) > 1:
                    # Ambiguous — pick first, flag for later disambiguation
                    rel.target_id = candidates[0]
                    rel.metadata["ambiguous"] = True
                    resolved.append(rel)
                else:
                    # External call — mark as unresolved/external
                    rel.metadata["external"] = True
                    resolved.append(rel)
            else:
                resolved.append(rel)
        return resolved
```

## 4.6 Where to Learn Tree-sitter (free resources)
- Official playground (test grammars live in browser): https://tree-sitter.github.io/tree-sitter/playground
- Using Parsers guide: https://tree-sitter.github.io/tree-sitter/using-parsers
- Node type reference per language: browse `node-types.json` in each grammar repo, e.g. https://github.com/tree-sitter/tree-sitter-python/blob/master/src/node-types.json

## 4.7 Testing Checkpoint
```python
# backend/tests/test_parser.py
def test_parses_python_function():
    parser = UniversalParser()
    entities, rels = parser.parse_file("samples/sample.py")
    assert any(e.type == "function" for e in entities)

def test_detects_function_calls():
    parser = UniversalParser()
    entities, rels = parser.parse_file("samples/sample.py")
    assert any(r.type == "calls" for r in rels)
```
**Expectation:** parsing a 500-line file should take <50ms. A 10,000-file repo should fully parse in under 60 seconds on a 4-core machine.

**Acceptance criteria for Phase 1:** Parser correctly extracts functions/classes for Python, JS/TS, Go from real sample repos with >90% entity-extraction accuracy (manually spot-check 20 functions).

---

# PART 5 — PHASE 2: GRAPH DATABASE (Weeks 2-4)

## 5.1 Install & Run ArcadeDB

```bash
docker run -d --name arcadedb \
  -p 2480:2480 -p 2424:2424 \
  -e JAVA_OPTS="-Xmx2g" \
  -v arcadedb_data:/home/arcadedb/databases \
  arcadedb/arcadedb:latest
```
Studio UI: http://localhost:2480 (default user: `root`, password set on first launch via logs — check `docker logs arcadedb`)

Docs: https://docs.arcadedb.com/

## 5.2 Python Client

```bash
pip install pyarcadedb  # community client, or use raw HTTP API via requests
```
If no mature client exists, use ArcadeDB's HTTP API directly (documented at https://docs.arcadedb.com/#HTTP-API):

```python
import requests

class ArcadeDBClient:
    def __init__(self, base_url="http://localhost:2480", db="codebase",
                 user="root", password="your_password"):
        self.base_url = base_url
        self.db = db
        self.auth = (user, password)

    def create_database(self):
        requests.post(f"{self.base_url}/api/v1/server",
                       json={"command": f"create database {self.db}"},
                       auth=self.auth)

    def execute_cypher(self, query: str, params: dict = None):
        resp = requests.post(
            f"{self.base_url}/api/v1/query/{self.db}/cypher",
            json={"command": query, "params": params or {}},
            auth=self.auth
        )
        resp.raise_for_status()
        return resp.json()["result"]

    def execute_command(self, command: str, params: dict = None):
        """For writes (CREATE, SET, etc.)"""
        resp = requests.post(
            f"{self.base_url}/api/v1/command/{self.db}/cypher",
            json={"command": command, "params": params or {}},
            auth=self.auth
        )
        resp.raise_for_status()
        return resp.json()["result"]
```

## 5.3 Full Graph Schema (write this exactly as Cypher setup)

```python
SCHEMA_SETUP = """
CREATE VERTEX TYPE File IF NOT EXISTS;
CREATE VERTEX TYPE Function IF NOT EXISTS;
CREATE VERTEX TYPE Class IF NOT EXISTS;
CREATE VERTEX TYPE Module IF NOT EXISTS;
CREATE VERTEX TYPE ExternalDependency IF NOT EXISTS;
CREATE VERTEX TYPE SecurityIssue IF NOT EXISTS;
CREATE VERTEX TYPE Author IF NOT EXISTS;
CREATE VERTEX TYPE TestFile IF NOT EXISTS;

CREATE EDGE TYPE CONTAINS IF NOT EXISTS;
CREATE EDGE TYPE CALLS IF NOT EXISTS;
CREATE EDGE TYPE IMPORTS IF NOT EXISTS;
CREATE EDGE TYPE INHERITS_FROM IF NOT EXISTS;
CREATE EDGE TYPE DEPENDS_ON IF NOT EXISTS;
CREATE EDGE TYPE AFFECTED_BY IF NOT EXISTS;
CREATE EDGE TYPE AUTHORED_BY IF NOT EXISTS;
CREATE EDGE TYPE COVERED_BY IF NOT EXISTS;

CREATE INDEX ON Function (id) UNIQUE;
CREATE INDEX ON Function (name) NOTUNIQUE;
CREATE INDEX ON File (path) UNIQUE;
CREATE INDEX ON Class (name) NOTUNIQUE;
"""
```

## 5.4 Bulk Ingestion (Batch Inserts — Critical for Performance)

```python
class GraphBuilder:
    def __init__(self, client: ArcadeDBClient):
        self.client = client

    def ingest_entities(self, entities: list[CodeEntity], batch_size=500):
        for i in range(0, len(entities), batch_size):
            batch = entities[i:i+batch_size]
            self._insert_batch(batch)

    def _insert_batch(self, batch: list[CodeEntity]):
        # Build one multi-statement transaction per batch
        statements = []
        for e in batch:
            label = e.type.capitalize()  # Function, Class
            statements.append(
                f"CREATE VERTEX {label} SET "
                f"id='{e.id}', name='{self._esc(e.name)}', "
                f"file_path='{self._esc(e.file_path)}', "
                f"language='{e.language}', "
                f"line_start={e.line_start}, line_end={e.line_end}, "
                f"cyclomatic_complexity={e.cyclomatic_complexity}, "
                f"lines_of_code={e.lines_of_code}"
            )
        full_command = "; ".join(statements)
        self.client.execute_command(full_command)

    def ingest_relationships(self, relationships: list[CodeRelationship], batch_size=500):
        for i in range(0, len(relationships), batch_size):
            batch = relationships[i:i+batch_size]
            for rel in batch:
                cmd = (
                    f"MATCH (a {{id: '{rel.source_id}'}}), (b {{id: '{rel.target_id}'}}) "
                    f"CREATE (a)-[:{rel.type.upper()}]->(b)"
                )
                try:
                    self.client.execute_command(cmd)
                except Exception:
                    pass  # target not found (external dep) — log and continue

    def _esc(self, s: str) -> str:
        return s.replace("'", "\\'")
```

**Performance target:** 500-statement batches should insert in <200ms each. A 50,000-entity codebase (≈100 batches) should fully ingest in under 30 seconds.

## 5.5 Incremental Update Strategy (SHA-256 based)

```python
class IncrementalUpdater:
    def __init__(self, graph_client, parser, file_hash_store: dict):
        self.client = graph_client
        self.parser = parser
        self.file_hash_store = file_hash_store  # persisted in a small key-value store (Redis/SQLite)

    def update_changed_files(self, repo_path: str):
        changed_files = []
        for file_path in walk_repository(repo_path):
            current_hash = file_hash(file_path)
            stored_hash = self.file_hash_store.get(file_path)
            if current_hash != stored_hash:
                changed_files.append(file_path)
                self.file_hash_store[file_path] = current_hash

        for file_path in changed_files:
            # 1. Delete all old entities for this file
            self.client.execute_command(
                f"MATCH (n {{file_path: '{file_path}'}}) DETACH DELETE n"
            )
            # 2. Re-parse and re-insert
            entities, rels = self.parser.parse_file(file_path)
            self.graph_builder.ingest_entities(entities)
            self.graph_builder.ingest_relationships(rels)

        return changed_files
```

**Expectation:** re-indexing 50 changed files out of a 5,000-file repo should complete in under 3 seconds.

## 5.6 Acceptance Criteria for Phase 2
- Can ingest a real-world repo (e.g., clone `flask` or `requests` from GitHub) and produce a queryable graph
- `MATCH (f:Function) RETURN count(f)` returns a sane number matching manual `grep -r "def "` count (±10%)
- Incremental update correctly removes stale nodes and adds new ones without duplicating

---

# PART 6 — PHASE 3: VECTOR DATABASE & EMBEDDINGS (Weeks 3-4)

## 6.1 Install

```bash
pip install chromadb sentence-transformers
```
Chroma can run embedded (no server) for dev, or as a Docker service for production:
```bash
docker run -d --name chroma -p 8000:8000 -v chroma_data:/chroma/chroma ghcr.io/chroma-core/chroma:latest
```

## 6.2 Embedding Model Setup

```python
from sentence_transformers import SentenceTransformer

# First run downloads ~130MB model from HuggingFace automatically
model = SentenceTransformer("BAAI/bge-small-en-v1.5")
```
Model card / download source: https://huggingface.co/BAAI/bge-small-en-v1.5
**Expectation:** model download takes 1-3 minutes on first run, then cached locally (`~/.cache/huggingface`).

## 6.3 AST-Aware Chunking Strategy

```python
class CodeChunker:
    """One chunk = one complete function/class/method. Never split mid-statement."""

    def chunk_entity(self, entity: CodeEntity) -> dict:
        # Build a rich text representation for embedding
        text_for_embedding = (
            f"# {entity.type}: {entity.name}\n"
            f"# File: {entity.file_path}\n"
            f"# Language: {entity.language}\n"
            f"{entity.docstring}\n"
            f"{entity.raw_code}"
        )
        return {
            "id": entity.id,
            "text": text_for_embedding,
            "metadata": {
                "entity_type": entity.type,
                "name": entity.name,
                "file_path": entity.file_path,
                "language": entity.language,
                "complexity": entity.cyclomatic_complexity,
                "loc": entity.lines_of_code,
            }
        }
```

## 6.4 Embedding Pipeline

```python
import chromadb

class VectorStoreBuilder:
    def __init__(self):
        self.client = chromadb.HttpClient(host="localhost", port=8000)
        self.collection = self.client.get_or_create_collection(
            name="codebase_embeddings",
            metadata={"hnsw:space": "cosine"}
        )
        self.model = SentenceTransformer("BAAI/bge-small-en-v1.5")
        self.chunker = CodeChunker()

    def embed_and_store(self, entities: list[CodeEntity], batch_size=64):
        chunks = [self.chunker.chunk_entity(e) for e in entities]

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            texts = [c["text"] for c in batch]
            embeddings = self.model.encode(texts, normalize_embeddings=True).tolist()

            self.collection.upsert(
                ids=[c["id"] for c in batch],
                embeddings=embeddings,
                documents=texts,
                metadatas=[c["metadata"] for c in batch]
            )

    def search(self, query: str, top_k: int = 10, filters: dict = None):
        query_embedding = self.model.encode([query], normalize_embeddings=True).tolist()
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
            where=filters
        )
        return results
```

**Performance:** embedding 10,000 functions on CPU (no GPU) takes roughly 3-6 minutes with `bge-small`. With a GPU, under 30 seconds.

## 6.5 Acceptance Criteria for Phase 3
- Querying "function that validates user passwords" returns relevant password/auth functions in top-5 results
- Embedding + storage for 1,000 entities completes in under 60 seconds on CPU
- Metadata filters (e.g., `language: python`) correctly narrow results

---

# PART 7 — PHASE 4: RISK DETECTION ENGINE (Weeks 5-7)

## 7.1 Full List of Risk Rules to Implement

| Risk | Detection Method | Severity | Cypher Pattern |
|---|---|---|---|
| Circular Dependency | Graph cycle detection | High | `MATCH p=(a:Module)-[:IMPORTS*2..6]->(a) RETURN p` |
| God Object | Class with >20 methods | High | `MATCH (c:Class)-[:CONTAINS]->(m:Function) WITH c, count(m) as n WHERE n>20 RETURN c` |
| Dead Code | Function with zero incoming CALLS | Medium | `MATCH (f:Function) WHERE NOT (f)<-[:CALLS]-() RETURN f` |
| Long Method | >100 lines | Low | filter `lines_of_code > 100` |
| High Complexity | Cyclomatic complexity >15 | Medium | filter `cyclomatic_complexity > 15` |
| Dependency Bloat | File importing >50 external modules | Medium | `MATCH (f:File)-[:IMPORTS]->(d:ExternalDependency) WITH f,count(d) as n WHERE n>50 RETURN f` |
| Shotgun Surgery | Function called from >30 distinct files | High | `MATCH (f:Function)<-[:CALLS]-(caller) WITH f, count(DISTINCT caller.file_path) as n WHERE n>30 RETURN f` |
| Orphan Module | File with no imports and not imported by anyone | Low | combination query |
| Deep Inheritance | Inheritance chain >5 levels | Medium | `MATCH p=(c:Class)-[:INHERITS_FROM*5..]->() RETURN p` |
| Untested Critical Path | High-complexity function with 0% test coverage | Critical | join complexity + coverage filter |

## 7.2 Risk Scorer Implementation

```python
class RiskDetector:
    def __init__(self, graph_client):
        self.client = graph_client

    def detect_circular_dependencies(self):
        query = "MATCH p=(a:Module)-[:IMPORTS*2..6]->(a) RETURN DISTINCT a.name, length(p) as cycle_length"
        results = self.client.execute_cypher(query)
        return [{"type": "circular_dependency", "severity": "high",
                 "target": r["a.name"], "details": f"Cycle of length {r['cycle_length']}"}
                for r in results]

    def detect_god_objects(self, threshold=20):
        query = f"""
        MATCH (c:Class)-[:CONTAINS]->(m:Function)
        WITH c, count(m) as method_count
        WHERE method_count > {threshold}
        RETURN c.name, c.file_path, method_count
        """
        results = self.client.execute_cypher(query)
        return [{"type": "god_object", "severity": "high",
                 "target": r["c.name"], "file": r["c.file_path"],
                 "details": f"{r['method_count']} methods (threshold: {threshold})"}
                for r in results]

    def detect_dead_code(self):
        query = """
        MATCH (f:Function)
        WHERE NOT (f)<-[:CALLS]-()
        RETURN f.name, f.file_path, f.lines_of_code
        """
        results = self.client.execute_cypher(query)
        return [{"type": "dead_code", "severity": "medium",
                 "target": r["f.name"], "file": r["f.file_path"]}
                for r in results]

    def detect_high_complexity(self, threshold=15):
        query = f"""
        MATCH (f:Function)
        WHERE f.cyclomatic_complexity > {threshold}
        RETURN f.name, f.file_path, f.cyclomatic_complexity
        ORDER BY f.cyclomatic_complexity DESC
        """
        results = self.client.execute_cypher(query)
        return [{"type": "high_complexity", "severity": "medium",
                 "target": r["f.name"], "file": r["f.file_path"],
                 "details": f"Complexity: {r['f.cyclomatic_complexity']}"}
                for r in results]

    def run_all_checks(self):
        all_risks = []
        all_risks += self.detect_circular_dependencies()
        all_risks += self.detect_god_objects()
        all_risks += self.detect_dead_code()
        all_risks += self.detect_high_complexity()
        return sorted(all_risks, key=lambda r: {"critical": 0, "high": 1,
                                                  "medium": 2, "low": 3}[r["severity"]])
```

## 7.3 Persisting Risks Back to Graph (for queryability)

```python
def persist_risks(client, risks: list[dict]):
    for risk in risks:
        cmd = f"""
        CREATE VERTEX SecurityIssue SET
        type='{risk['type']}', severity='{risk['severity']}',
        target='{risk['target']}', details='{risk.get('details', '')}'
        """
        client.execute_command(cmd)
```

## 7.4 Acceptance Criteria for Phase 4
- Running risk detection on a known messy codebase (e.g., an old legacy project) correctly flags >5 real god objects/dead functions verified by manual inspection
- False positive rate <20% (spot-check 30 flagged items)
- Full risk scan on 10,000-entity graph completes in under 15 seconds

---

# PART 8 — PHASE 5: CHANGE IMPACT / BLAST RADIUS ANALYSIS (Week 7)

```python
class ImpactAnalyzer:
    def __init__(self, graph_client):
        self.client = graph_client

    def analyze_file_impact(self, file_path: str, max_depth: int = 5):
        query = f"""
        MATCH (f:File {{path: '{file_path}'}})-[:CONTAINS]->(entity)
        MATCH path = (entity)<-[:CALLS*1..{max_depth}]-(affected)
        RETURN DISTINCT affected.name, affected.file_path, length(path) as hops
        ORDER BY hops ASC
        """
        results = self.client.execute_cypher(query)

        direct = [r for r in results if r["hops"] == 1]
        transitive = [r for r in results if r["hops"] > 1]

        return {
            "file": file_path,
            "directly_affected_count": len(direct),
            "transitively_affected_count": len(transitive),
            "directly_affected": direct,
            "transitively_affected": transitive[:50],  # cap for response size
            "risk_level": self._compute_risk_level(len(direct), len(transitive)),
        }

    def _compute_risk_level(self, direct_count, transitive_count) -> str:
        total = direct_count + transitive_count
        if total > 50: return "critical"
        if total > 20: return "high"
        if total > 5: return "medium"
        return "low"

    def find_affected_tests(self, file_path: str):
        query = f"""
        MATCH (f:File {{path: '{file_path}'}})-[:CONTAINS]->(entity)
        MATCH (entity)-[:COVERED_BY]->(t:TestFile)
        RETURN DISTINCT t.path
        """
        return self.client.execute_cypher(query)
```

**Expectation:** for a typical "utility function" in a mid-size codebase, blast radius should return 5-50 affected functions. For a core/shared module, expect 100+.

---

# PART 9 — PHASE 6: HYBRID RETRIEVAL + LLM QUERY ENGINE (Weeks 8-10)

## 9.1 Query Router

```python
STRUCTURAL_KEYWORDS = {
    "calls", "called by", "imports", "imported by", "inherits",
    "depends on", "dependency", "references", "uses", "affected by",
    "blast radius", "impact", "who calls", "what calls"
}

class QueryRouter:
    def classify(self, question: str) -> str:
        q_lower = question.lower()
        if any(kw in q_lower for kw in STRUCTURAL_KEYWORDS):
            return "structural"
        return "semantic"
```

## 9.2 LLM-to-Cypher Translator (with few-shot prompting)

```python
import requests

CYPHER_FEWSHOT = """
You translate English questions about a codebase into Cypher graph queries.
Schema: (:File)-[:CONTAINS]->(:Function|:Class)
        (:Function)-[:CALLS]->(:Function)
        (:File)-[:IMPORTS]->(:Module)
        (:Class)-[:INHERITS_FROM]->(:Class)

Examples:
Q: "What functions call validate_user?"
A: MATCH (f:Function)-[:CALLS]->(t:Function {name:'validate_user'}) RETURN f.name, f.file_path

Q: "Which classes inherit from BaseModel?"
A: MATCH (c:Class)-[:INHERITS_FROM]->(b:Class {name:'BaseModel'}) RETURN c.name

Q: "What does auth.py import?"
A: MATCH (f:File {path:'auth.py'})-[:IMPORTS]->(m:Module) RETURN m.name

Now translate this question. Return ONLY the Cypher query, nothing else.
Q: "{question}"
A:"""

class OllamaClient:
    def __init__(self, base_url="http://localhost:11434", model="mistral"):
        self.base_url = base_url
        self.model = model

    def generate(self, prompt: str, temperature=0.2) -> str:
        resp = requests.post(f"{self.base_url}/api/generate", json={
            "model": self.model, "prompt": prompt,
            "temperature": temperature, "stream": False
        }, timeout=120)
        return resp.json()["response"].strip()

class CypherGenerator:
    def __init__(self, llm_client: OllamaClient):
        self.llm = llm_client

    def generate_cypher(self, question: str) -> str:
        prompt = CYPHER_FEWSHOT.replace("{question}", question)
        raw = self.llm.generate(prompt)
        # Strip markdown fences if model adds them
        return raw.replace("```cypher", "").replace("```", "").strip()
```

## 9.3 Hybrid Retriever (Full Implementation)

```python
class HybridRetriever:
    def __init__(self, graph_client, vector_store, cypher_gen, router):
        self.graph = graph_client
        self.vectors = vector_store
        self.cypher_gen = cypher_gen
        self.router = router

    def retrieve(self, question: str, top_k=10):
        strategy = self.router.classify(question)

        if strategy == "structural":
            try:
                cypher = self.cypher_gen.generate_cypher(question)
                results = self.graph.execute_cypher(cypher)
                if results:
                    return {"strategy": "structural", "cypher": cypher, "results": results}
            except Exception:
                pass  # fall through to semantic search

        # Semantic search (default or fallback)
        vector_results = self.vectors.search(question, top_k=top_k)
        return {"strategy": "semantic", "results": vector_results}
```

## 9.4 Answer Generator

```python
ANSWER_PROMPT = """You are a senior software architect analyzing a codebase.
Answer the question using ONLY the provided context. Cite file paths and function names.
If the context doesn't contain the answer, say so clearly.

Question: {question}

Context:
{context}

Answer (be concise, cite sources):"""

class AnswerGenerator:
    def __init__(self, llm_client: OllamaClient):
        self.llm = llm_client

    def generate(self, question: str, retrieval_result: dict) -> str:
        context = self._format_context(retrieval_result)
        prompt = ANSWER_PROMPT.format(question=question, context=context)
        return self.llm.generate(prompt, temperature=0.3)

    def _format_context(self, retrieval_result: dict) -> str:
        if retrieval_result["strategy"] == "structural":
            return "\n".join(str(r) for r in retrieval_result["results"][:20])
        else:
            docs = retrieval_result["results"].get("documents", [[]])[0]
            metas = retrieval_result["results"].get("metadatas", [[]])[0]
            return "\n---\n".join(
                f"File: {m.get('file_path')}\nFunction: {m.get('name')}\nCode:\n{d[:500]}"
                for d, m in zip(docs, metas)
            )
```

## 9.5 Acceptance Criteria for Phase 6
- Test against 20 hand-written questions (10 structural, 10 semantic): >70% return correct/useful answers
- Structural query latency <3 sec (includes LLM Cypher generation)
- Semantic query latency <1 sec
- LLM never hallucinates a file path that doesn't exist in the context (verify manually)

---

# PART 10 — PHASE 7: FASTAPI BACKEND (Weeks 10-11)

## 10.1 Full Project Structure
```
backend/
├── main.py
├── config.py
├── api/
│   ├── routes_ingest.py
│   ├── routes_query.py
│   ├── routes_impact.py
│   ├── routes_risks.py
│   └── routes_stats.py
├── celery_app.py
├── tasks.py
└── requirements.txt
```

## 10.2 `requirements.txt`
```
fastapi==0.110.0
uvicorn[standard]==0.27.0
celery==5.3.6
redis==5.0.1
tree-sitter==0.21.0
tree-sitter-languages==1.10.2
chromadb==0.4.24
sentence-transformers==2.5.1
requests==2.31.0
GitPython==3.1.42
python-multipart==0.0.9
pydantic==2.6.1
prometheus-client==0.20.0
pytest==8.0.2
```

## 10.3 `main.py`
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import routes_ingest, routes_query, routes_impact, routes_risks, routes_stats

app = FastAPI(
    title="Codebase Intelligence API",
    description="AI-powered architecture analysis for codebases",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"], allow_headers=["*"],
)

app.include_router(routes_ingest.router, prefix="/api/v1", tags=["ingest"])
app.include_router(routes_query.router, prefix="/api/v1", tags=["query"])
app.include_router(routes_impact.router, prefix="/api/v1", tags=["impact"])
app.include_router(routes_risks.router, prefix="/api/v1", tags=["risks"])
app.include_router(routes_stats.router, prefix="/api/v1", tags=["stats"])

@app.get("/health")
def health(): return {"status": "ok"}
```
Run: `uvicorn main:app --reload --port 8000`
Auto-generated docs at: http://localhost:8000/docs (FastAPI's built-in Swagger UI)

## 10.4 Full Endpoint Reference

| Method | Path | Purpose | Request Body | Response |
|---|---|---|---|---|
| POST | `/api/v1/ingest` | Start repo ingestion | `{"repo_url": str}` | `{"job_id": str, "status": "queued"}` |
| GET | `/api/v1/ingest/{job_id}` | Check ingestion progress | — | `{"status": str, "progress": float}` |
| GET | `/api/v1/query` | Natural language question | query param `q` | `{"answer": str, "sources": list, "strategy": str}` |
| GET | `/api/v1/impact/{file_path}` | Blast radius | query param `depth` | `{"directly_affected": list, ...}` |
| GET | `/api/v1/risks` | List architecture risks | query param `severity` | `{"risks": list, "total": int}` |
| GET | `/api/v1/stats` | Codebase statistics | — | `{"total_functions": int, ...}` |
| GET | `/api/v1/function/{id}` | Function detail | — | `{"entity": {}, "callers": [], "callees": []}` |
| GET | `/api/v1/graph/{entity_id}` | Subgraph for visualization | query param `depth` | `{"nodes": [], "edges": []}` |

## 10.5 Celery + Redis Setup

```python
# celery_app.py
from celery import Celery
celery_app = Celery("codebase_intelligence",
                     broker="redis://localhost:6379/0",
                     backend="redis://localhost:6379/1")

# tasks.py
@celery_app.task(bind=True)
def ingest_repository_task(self, repo_url: str):
    self.update_state(state="PROGRESS", meta={"step": "cloning"})
    repo_path = clone_repo(repo_url)

    self.update_state(state="PROGRESS", meta={"step": "parsing"})
    entities, relationships = parse_all_files(repo_path)

    self.update_state(state="PROGRESS", meta={"step": "building_graph"})
    graph_builder.ingest_entities(entities)
    graph_builder.ingest_relationships(relationships)

    self.update_state(state="PROGRESS", meta={"step": "embedding"})
    vector_builder.embed_and_store(entities)

    self.update_state(state="PROGRESS", meta={"step": "risk_analysis"})
    risks = risk_detector.run_all_checks()
    persist_risks(graph_client, risks)

    return {"status": "complete", "entities": len(entities), "risks": len(risks)}
```
Run worker: `celery -A celery_app worker --loglevel=info --concurrency=2`

## 10.6 Acceptance Criteria for Phase 7
- `POST /api/v1/ingest` with a real GitHub URL successfully triggers full pipeline end-to-end
- All endpoints documented and testable via `/docs`
- Ingestion job status correctly transitions: queued → cloning → parsing → building_graph → embedding → risk_analysis → complete

---

# PART 11 — PHASE 8: NEXT.JS FRONTEND (Weeks 11-13)

## 11.1 Project Setup

```bash
npx create-next-app@latest frontend --typescript --tailwind --app
cd frontend
npm install recharts react-force-graph-2d axios swr lucide-react
```

## 11.2 Full Page Inventory

| Route | Purpose | Key Components |
|---|---|---|
| `/` | Landing / repo input | RepoInputForm, RecentRepos |
| `/dashboard` | Stats overview | StatsGrid, LanguageChart, TopRisksCard |
| `/query` | NL search interface | SearchBox, AnswerCard, SourceCitations |
| `/graph` | Interactive dependency graph | ForceGraph2D, NodeDetailsPanel, FilterControls |
| `/risks` | Full risk list with filters | RiskTable, SeverityFilter, RiskDetailModal |
| `/impact/[filePath]` | Blast radius for one file | BlastRadiusGraph, AffectedFilesList, AffectedTestsList |
| `/function/[id]` | Function deep-dive | CodeViewer, CallersCallees, ComplexityBadge |

## 11.3 Example: Query Page (`app/query/page.tsx`)

```tsx
"use client"
import { useState } from "react"
import axios from "axios"

export default function QueryPage() {
  const [question, setQuestion] = useState("")
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)

  const handleSearch = async () => {
    setLoading(true)
    const res = await axios.get(`http://localhost:8000/api/v1/query`, {
      params: { q: question }
    })
    setResult(res.data)
    setLoading(false)
  }

  return (
    <div className="max-w-3xl mx-auto py-12 px-4">
      <h1 className="text-2xl font-bold mb-6">Ask Your Codebase</h1>
      <div className="flex gap-2">
        <input
          className="flex-1 border rounded-lg px-4 py-2"
          placeholder="What does the auth module depend on?"
          value={question}
          onChange={e => setQuestion(e.target.value)}
          onKeyDown={e => e.key === "Enter" && handleSearch()}
        />
        <button
          onClick={handleSearch}
          className="bg-black text-white px-6 py-2 rounded-lg"
        >
          {loading ? "Thinking..." : "Ask"}
        </button>
      </div>

      {result && (
        <div className="mt-8 border rounded-lg p-6 bg-gray-50">
          <p className="text-sm text-gray-500 mb-2">
            Strategy: {result.strategy}
          </p>
          <p className="whitespace-pre-wrap">{result.answer}</p>
          {result.sources?.length > 0 && (
            <div className="mt-4">
              <p className="font-semibold text-sm">Sources:</p>
              <ul className="text-sm text-gray-600">
                {result.sources.map((s: string, i: number) => (
                  <li key={i}>📄 {s}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
```

## 11.4 Graph Visualization Component (`components/CodeGraph.tsx`)

```tsx
"use client"
import dynamic from "next/dynamic"
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false })

export default function CodeGraph({ data }: { data: { nodes: any[], links: any[] } }) {
  return (
    <ForceGraph2D
      graphData={data}
      nodeLabel="name"
      nodeAutoColorBy="type"
      linkDirectionalArrowLength={4}
      onNodeClick={(node: any) => window.location.href = `/function/${node.id}`}
      height={700}
    />
  )
}
```

## 11.5 Acceptance Criteria for Phase 8
- All 7 pages render without errors against a live backend
- Graph visualization handles 500+ nodes without freezing the browser
- Query page correctly displays answer + sources for a real question
- Mobile-responsive (Tailwind breakpoints tested at 375px, 768px, 1280px)

---

# PART 12 — PHASE 9: DOCKER & DEPLOYMENT (Weeks 12-14)

## 12.1 Full `docker-compose.yml`

```yaml
version: '3.8'

services:
  arcadedb:
    image: arcadedb/arcadedb:latest
    ports: ["2480:2480", "2424:2424"]
    environment:
      JAVA_OPTS: "-Xmx2g"
      arcadedb.server.rootPassword: "ChangeMe123!"
    volumes: ["arcadedb_data:/home/arcadedb/databases"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:2480"]
      interval: 10s
      retries: 5

  chroma:
    image: ghcr.io/chroma-core/chroma:latest
    ports: ["8000:8000"]
    volumes: ["chroma_data:/chroma/chroma"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  ollama:
    image: ollama/ollama
    ports: ["11434:11434"]
    volumes: ["ollama_models:/root/.ollama"]
    # Uncomment for GPU:
    # deploy:
    #   resources:
    #     reservations:
    #       devices: [{driver: nvidia, count: 1, capabilities: [gpu]}]

  backend:
    build: ./backend
    ports: ["8001:8000"]
    environment:
      ARCADEDB_URL: "http://arcadedb:2480"
      CHROMA_URL: "http://chroma:8000"
      OLLAMA_URL: "http://ollama:11434"
      REDIS_URL: "redis://redis:6379/0"
    depends_on: [arcadedb, chroma, redis, ollama]
    volumes: ["./backend:/app"]

  celery_worker:
    build: ./backend
    command: celery -A celery_app worker --loglevel=info --concurrency=2
    environment:
      ARCADEDB_URL: "http://arcadedb:2480"
      CHROMA_URL: "http://chroma:8000"
      OLLAMA_URL: "http://ollama:11434"
      REDIS_URL: "redis://redis:6379/0"
    depends_on: [redis, arcadedb]

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    environment:
      NEXT_PUBLIC_API_URL: "http://localhost:8001"
    depends_on: [backend]

volumes:
  arcadedb_data:
  chroma_data:
  ollama_models:
```

## 12.2 `backend/Dockerfile`
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 12.3 `frontend/Dockerfile`
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json .
RUN npm install
COPY . .
RUN npm run build
CMD ["npm", "start"]
```

## 12.4 First-Run Bootstrap Script (`scripts/setup.sh`)
```bash
#!/bin/bash
set -e
echo "Pulling Ollama model..."
docker compose up -d ollama
sleep 5
docker exec -it $(docker compose ps -q ollama) ollama pull mistral

echo "Starting full stack..."
docker compose up -d

echo "Waiting for services..."
sleep 15

echo "Done! Visit http://localhost:3000"
```

## 12.5 Free/Cheap Hosting Options (where to deploy)
| Provider | Free Tier | Recommended Tier | Cost | Link |
|---|---|---|---|---|
| Hetzner Cloud | None | CX21 (4GB RAM, 2vCPU) | ~€5.83/mo | https://www.hetzner.com/cloud |
| Oracle Cloud | **Always Free** (4 ARM cores, 24GB RAM!) | Free tier sufficient for MVP | $0 | https://www.oracle.com/cloud/free |
| Railway.app | $5 free credit/mo | Hobby plan | ~$5-10/mo | https://railway.app |
| Fly.io | Free allowances | Shared CPU 1x | ~$0-5/mo | https://fly.io |
| DigitalOcean | $200 credit (new accounts) | Basic Droplet 4GB | ~$24/mo | https://digitalocean.com |

**Recommendation:** Start on **Oracle Cloud Free Tier** (genuinely free forever, 24GB RAM ARM instance) — sufficient to run the entire stack including Ollama with a 7B model.

## 12.6 Acceptance Criteria for Phase 9
- `docker compose up` from a clean clone brings up all 6 services successfully
- Full pipeline (ingest → query) works end-to-end inside Docker network
- Deployed instance on Oracle Free Tier handles a 10,000-line repo ingestion without OOM

---

# PART 13 — FULL FEATURE CATALOG (Complete List)

## 13.1 Core Features (MVP — Must Have)
1. Multi-language AST parsing (Python, JS, TS, Go minimum)
2. Knowledge graph construction (functions, classes, files, imports, calls)
3. Incremental re-indexing on file change
4. Semantic code search (vector similarity)
5. Structural graph queries (Cypher, NL-to-Cypher)
6. Hybrid retrieval combining both
7. Natural-language Q&A with citations
8. Change impact / blast radius analysis
9. 5+ architecture risk detectors
10. REST API with OpenAPI docs
11. Web dashboard (stats, query, risks, graph view)
12. Docker Compose one-command deployment

## 13.2 Advanced Features (v1.1 — Should Have)
13. Code ownership mapping (git blame integration)
14. Test coverage overlay on graph
15. PR/commit-level impact analysis (CI integration)
16. Refactoring recommendations (god object splits, dead code removal)
17. Multi-repo support (analyze microservice fleets together)
18. Historical trend tracking (complexity over time)
19. Export reports (PDF/Markdown architecture summaries)
20. GitHub Action for automated PR comments with impact analysis

## 13.3 Stretch Features (v2+ — Nice to Have)
21. IDE plugin (VSCode extension querying the API)
22. Multi-agent refactoring assistant (LangChain agent with tools)
23. Security smell detection (hardcoded secrets, SQL injection patterns)
24. Data flow analysis (taint tracking across function boundaries)
25. API contract drift detection (OpenAPI spec diffing)
26. Slack/Discord bot for natural-language codebase queries
27. Fine-tuned local model on your specific codebase patterns
28. 3D graph visualization (Three.js)
29. Microservice topology auto-discovery
30. Cost/complexity estimation for proposed changes

## 13.4 Feature → Phase Mapping
| Feature # | Implemented in Phase |
|---|---|
| 1-2 | Phase 1-2 |
| 3 | Phase 2 (incremental updater) |
| 4-6 | Phase 3 + 6 |
| 7 | Phase 6 |
| 8 | Phase 5 |
| 9 | Phase 4 |
| 10-12 | Phase 7-9 |
| 13-20 | Phase 10+ (post-MVP) |
| 21-30 | v2 roadmap |

---

# PART 14 — TESTING STRATEGY (Full Detail)

## 14.1 Unit Test Coverage Targets
| Module | Target Coverage |
|---|---|
| `ast_parser/` | 85% |
| `graph_db/` | 75% |
| `vector_db/` | 75% |
| `risk_detection/` | 90% |
| `retrieval/` | 70% |
| `api/` | 80% |

## 14.2 Sample Test Repos to Validate Against (use these specific public repos)
- **Small Python:** https://github.com/psf/requests (~10K LOC) — clean, well-documented
- **Medium JS:** https://github.com/expressjs/express (~15K LOC)
- **Large polyglot:** https://github.com/home-assistant/core (huge, good stress test — use a subdirectory)
- **Known messy legacy:** find any abandoned student/hackathon project on GitHub for risk-detection testing

## 14.3 Integration Test Script
```python
# tests/test_e2e.py
import pytest

@pytest.mark.integration
def test_full_pipeline_on_requests_repo():
    repo_path = clone_test_repo("https://github.com/psf/requests")
    entities, rels = parser.parse_repository(repo_path)
    assert len(entities) > 100

    graph_builder.ingest_entities(entities)
    graph_builder.ingest_relationships(rels)

    vector_builder.embed_and_store(entities)

    answer = query_engine.ask("What does the Session class do?")
    assert "session" in answer.lower()

    risks = risk_detector.run_all_checks()
    assert isinstance(risks, list)
```

## 14.4 Load Testing (use `locust`, free)
```bash
pip install locust
```
```python
# locustfile.py
from locust import HttpUser, task

class APIUser(HttpUser):
    @task
    def query(self):
        self.client.get("/api/v1/query?q=what+functions+call+login")
```
```bash
locust -f locustfile.py --host=http://localhost:8001
```
**Target:** sustain 20 concurrent users with <3s p95 latency on the `/query` endpoint.

---

# PART 15 — MONITORING & OBSERVABILITY (Weeks 20-21)

## 15.1 Prometheus + Grafana (Docker addition)

```yaml
  prometheus:
    image: prom/prometheus
    ports: ["9090:9090"]
    volumes: ["./infra/prometheus.yml:/etc/prometheus/prometheus.yml"]

  grafana:
    image: grafana/grafana
    ports: ["3001:3000"]
    volumes: ["grafana_data:/var/lib/grafana"]
```

`infra/prometheus.yml`:
```yaml
scrape_configs:
  - job_name: 'backend'
    static_configs:
      - targets: ['backend:8000']
```

## 15.2 Metrics to Track
```python
from prometheus_client import Counter, Histogram

QUERY_LATENCY = Histogram("query_latency_seconds", "Query endpoint latency")
INGESTION_DURATION = Histogram("ingestion_duration_seconds", "Full repo ingestion time")
LLM_CALLS = Counter("llm_calls_total", "Total LLM generation calls")
RISKS_DETECTED = Counter("risks_detected_total", "Total risks found", ["severity"])
GRAPH_NODE_COUNT = Counter("graph_nodes_total", "Total nodes in graph")
```

## 15.3 Dashboards to Build in Grafana
1. **API Health:** request rate, error rate, p50/p95/p99 latency per endpoint
2. **Ingestion Pipeline:** jobs queued/running/complete, avg duration per phase
3. **LLM Usage:** calls per minute, avg generation time, token throughput estimate
4. **Risk Trends:** risks detected over time by severity

---

# PART 16 — DOCUMENTATION & OPEN-SOURCE READINESS CHECKLIST

- [ ] `README.md` with: project description, architecture diagram, quickstart (`docker compose up`), screenshots/GIF demo
- [ ] `CONTRIBUTING.md`: dev setup, coding standards, PR process
- [ ] `LICENSE` (Apache 2.0)
- [ ] `CODE_OF_CONDUCT.md` (use Contributor Covenant: https://www.contributor-covenant.org/)
- [ ] `/docs` folder with architecture decision records (ADRs)
- [ ] OpenAPI docs auto-served at `/docs` (FastAPI gives this for free)
- [ ] GitHub Actions CI: lint + test on every PR
- [ ] GitHub issue templates (bug report, feature request)
- [ ] Demo video or animated GIF in README (use free tool: https://www.screentogif.com or asciinema for terminal demos: https://asciinema.org)
- [ ] Badge row in README: build status, license, Docker pulls

## 16.1 Sample GitHub Actions CI (`.github/workflows/ci.yml`)
```yaml
name: CI
on: [push, pull_request]
jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.11'}
      - run: pip install -r backend/requirements.txt
      - run: pytest backend/tests/ -v

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: {node-version: '20'}
      - run: cd frontend && npm install && npm run build
```

---

# PART 17 — COST BREAKDOWN (Real Numbers)

| Item | Cost |
|---|---|
| All software/libraries | $0 (Apache 2.0/MIT) |
| Oracle Cloud Free Tier hosting | $0/month (permanent free tier) |
| Domain name (optional, for demo) | ~$10-12/year (Namecheap/Porkbun) |
| GitHub (public repo, Actions) | $0 |
| HuggingFace model downloads | $0 |
| Ollama models | $0 |
| **Total to launch v1.0** | **$0–12 (just optional domain)** |

If you outgrow Oracle Free Tier (24GB RAM ARM):
- Hetzner CX31 (8GB RAM): ~€11.90/month
- This handles repos up to ~500K LOC comfortably

---

# PART 18 — WEEK-BY-WEEK MASTER TIMELINE

| Week | Focus | Deliverable | Acceptance Test |
|---|---|---|---|
| 1 | Project setup + Tree-sitter basics | Repo skeleton, parser parses 1 language | `pytest test_parser.py` passes |
| 2 | Multi-language parser + symbol resolution | Parser handles 4+ languages | Manual spot-check 90% accuracy |
| 3 | ArcadeDB setup + schema | Graph DB running, schema created | Can manually insert/query via Studio UI |
| 4 | Graph ingestion pipeline | Full repo → graph in <60s | Ingest `requests` repo successfully |
| 5 | Chroma + embeddings | Vector search returns relevant results | Top-5 recall test on 10 queries |
| 6 | Risk detection (5 rules) | Risk scanner runs on real repo | <20% false positive rate |
| 7 | Impact analysis | Blast radius endpoint working | Matches manual analysis on 3 test cases |
| 8 | Query router + Cypher gen | NL→Cypher works for 10 sample Qs | 70%+ correct Cypher generated |
| 9 | Hybrid retriever + answer gen | End-to-end Q&A working | 70%+ answer quality (manual eval) |
| 10 | FastAPI backend | All endpoints live, Celery jobs working | Full ingest job completes via API |
| 11 | Frontend setup + dashboard | Dashboard + query page live | Loads real data from backend |
| 12 | Frontend graph viz + risk page | All 7 pages complete | Manual UX walkthrough |
| 13 | Polish frontend, responsive design | Mobile-tested UI | Works at 375px-1920px |
| 14 | Docker Compose full stack | `docker compose up` works clean | Fresh clone → working app in <10 min |
| 15 | Deploy to Oracle Cloud | Live public demo URL | Accessible externally |
| 16-17 | Multi-agent features (optional) | LangChain agent w/ tools | Agent completes 3-step task |
| 18-19 | Security scanning rules | SAST rule engine | Detects 3+ known vuln patterns |
| 20-21 | Monitoring stack | Grafana dashboards live | Metrics visible in real-time |
| 22-23 | Testing + bug bash | 80%+ coverage, E2E suite | CI green on all tests |
| 24 | Documentation + launch | README, demo video, public release | Post on GitHub, HN, Reddit r/opensource |

---

# PART 19 — TROUBLESHOOTING GUIDE (Common Issues)

| Problem | Likely Cause | Fix |
|---|---|---|
| Tree-sitter `ImportError` | Missing compiled grammar | Use `tree-sitter-languages` (prebuilt) instead of building from source |
| ArcadeDB connection refused | Container not fully started | Wait 10-15s after `docker compose up`, check `docker logs arcadedb` |
| Chroma slow on first query | Model loading into memory | Expected — first query after restart takes longer; subsequent queries are fast |
| Ollama out of memory | Model too large for available RAM | Use `mistral` (7B, ~5GB) instead of larger models; check `ollama ps` |
| Cypher query syntax errors from LLM | Few-shot prompt too sparse | Add more examples matching your exact schema; lower temperature to 0.1 |
| Graph ingestion duplicating nodes | Missing unique constraint check | Use `MERGE` instead of `CREATE` for idempotent inserts, or check-before-insert |
| Celery tasks stuck in PENDING | Worker not running or wrong broker URL | Verify `celery -A celery_app worker` is running and Redis is reachable |
| Frontend CORS errors | Backend CORS misconfigured | Check `allow_origins` includes exact frontend URL (with port) |

---

# PART 20 — LEARNING RESOURCES INDEX (All Free)

| Topic | Resource | Link |
|---|---|---|
| Tree-sitter | Official docs + playground | https://tree-sitter.github.io/tree-sitter/ |
| Cypher query language | Neo4j's free Cypher manual (syntax is compatible) | https://neo4j.com/docs/cypher-manual/current/ |
| ArcadeDB | Official docs | https://docs.arcadedb.com/ |
| Graph algorithms (community detection, centrality) | Free textbook: "Graph Algorithms" preview chapters | https://neo4j.com/graph-algorithms-book/ |
| ChromaDB | Official docs | https://docs.trychroma.com |
| Sentence Transformers | Official docs + model hub | https://www.sbert.net |
| Ollama | Official docs | https://github.com/ollama/ollama/blob/main/docs/api.md |
| RAG fundamentals | "From Local to Global" GraphRAG paper (free arXiv) | https://arxiv.org/abs/2404.16130 |
| FastAPI | Official tutorial (excellent, free) | https://fastapi.tiangolo.com/tutorial/ |
| Celery | Official docs | https://docs.celeryq.dev/en/stable/ |
| Next.js 14 | Official learn course (free, interactive) | https://nextjs.org/learn |
| D3.js force graphs | Observable examples (free) | https://observablehq.com/@d3/force-directed-graph |
| Docker Compose | Official docs | https://docs.docker.com/compose/ |
| System design for this kind of platform | "Designing Data-Intensive Applications" (book, library/torrent legally via public library apps like Libby) | — |

---

# PART 21 — FINAL ACCEPTANCE CHECKLIST (v1.0 Launch)

- [ ] Parses Python, JavaScript/TypeScript, Go, and at least one more language correctly
- [ ] Knowledge graph contains accurate CONTAINS/CALLS/IMPORTS/INHERITS_FROM edges
- [ ] Incremental updates work without full re-index
- [ ] Vector search returns relevant results for 8/10 test queries
- [ ] Hybrid Q&A answers 7/10 test questions correctly with citations
- [ ] 5+ risk detectors implemented with documented false-positive rate
- [ ] Blast radius analysis validated against 3 manual test cases
- [ ] All API endpoints documented in OpenAPI/Swagger
- [ ] Frontend has working dashboard, query, graph, risks, and impact pages
- [ ] `docker compose up` works on a fresh machine in under 10 minutes
- [ ] Deployed to a public URL (even if just Oracle Free Tier)
- [ ] README has architecture diagram, quickstart, and demo GIF/video
- [ ] CI pipeline green (tests + lint pass on every push)
- [ ] License (Apache 2.0) applied, CONTRIBUTING.md written
- [ ] At least 3 real external repos tested end-to-end without crashing

---

This document is the complete, step-by-step source of truth for building the platform from zero to a public open-source v1.0 launch — entirely on free and open-source infrastructure.

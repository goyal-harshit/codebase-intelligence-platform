# Enterprise Codebase Intelligence Platform - Complete Roadmap

## Executive Summary
A production-ready, open-source AI-powered system analyzing enterprise codebases through AST parsing, knowledge graphs, and natural language queries. Using 100% free tools: Tree-sitter + ArcadeDB/Neo4j-Community + Ollama + Chroma for RAG.

---

## Part I: Foundation & Architecture

### Phase 1: Core Technology Stack (Weeks 1-2)

#### 1.1 AST Parsing Engine
**Goal:** Extract code structure from polyglot repositories

**Tools & Stack:**
- **Tree-sitter** (0-cost, language-agnostic AST parser)
  - Supports 50+ languages: Python, JS/TS, Go, Rust, Java, C++, C#, Ruby, PHP, Swift, Kotlin, Scala, Solidity, etc.
  - ~1000+ files/sec parsing performance
  - Used by VS Code, Neovim, GitHub Copilot

- **Language-Specific Parsers (optional fallbacks)**
  - Python: `ast` module (stdlib)
  - Go: `go/parser` (stdlib)
  - Rust: `syn` crate (free)

**Deliverables:**
```python
class CodeEntity:
    id: str
    type: str  # "function", "class", "module", "variable"
    name: str
    file_path: str
    line_start: int
    line_end: int
    signature: str
    docstring: str
    complexity_metrics: {
        cyclomatic_complexity: int,
        lines_of_code: int,
        depth: int
    }

class CodeRelationship:
    source_id: str
    target_id: str
    type: str  # "calls", "imports", "inherits", "references", "dataflow"
    metadata: dict
```

**Implementation Steps:**
1. Install Tree-sitter: `npm install tree-sitter` or `pip install tree-sitter`
2. Create language bindings for top 10 supported languages
3. Build incremental parser with file-change detection (SHA-256 hash tracking)
4. Implement symbol resolution (identify unresolved external dependencies)
5. Extract metrics: cyclomatic complexity, LOC, call depth

---

### Phase 2: Knowledge Graph Backend (Weeks 2-4)

#### 2.1 Graph Database Selection

**Recommended: ArcadeDB (Apache 2.0 licensed, Neo4j-compatible)**
- Cypher query support (migrate from Neo4j anytime)
- Multi-model: graph + document + key-value
- Free, no data caps, no licensing restrictions
- Docker deployment ready

**Alternative: Neo4j Community Edition**
- Single-instance limit (no clustering)
- More mature ecosystem, extensive docs
- Larger community

**Setup:**
```bash
# ArcadeDB Docker
docker run -d --name arcadedb -p 2480:2480 -p 2424:2424 arcadedb/arcadedb

# Neo4j Community Docker
docker run -d --name neo4j -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:community
```

#### 2.2 Graph Schema Design

**Core Node Types:**
```cypher
(:File)
  - path: string
  - language: string
  - lines_of_code: int
  - last_modified: datetime

(:Function)
  - name: string
  - signature: string
  - cyclomatic_complexity: int
  - docstring: string

(:Class)
  - name: string
  - inheritance_chain: list
  - visibility: enum ["public", "private", "protected"]

(:Module)
  - name: string
  - exports: list

(:ExternalDependency)
  - package_name: string
  - version: string
  - is_resolved: boolean

(:SecurityIssue)
  - rule_id: string
  - severity: enum ["critical", "high", "medium", "low"]
  - description: string
```

**Relationship Types:**
```cypher
(:File) -[:CONTAINS]-> (:Function)
(:File) -[:IMPORTS]-> (:Module)
(:Function) -[:CALLS]-> (:Function)
(:Function) -[:CALLS]-> (:ExternalDependency)
(:Class) -[:INHERITS_FROM]-> (:Class)
(:Function) -[:DEPENDS_ON]-> (:ExternalDependency)
(:Function) -[:AFFECTED_BY]-> (:SecurityIssue)
(:Module) -[:HAS_ARCHITECTURE_RISK]-> (:SecurityIssue)
```

#### 2.3 Data Ingestion Pipeline

**Implementation:**
```python
# Pseudocode
class KnowledgeGraphBuilder:
    def __init__(self, graph_db: ArcadeDB):
        self.db = graph_db
    
    def ingest_codebase(self, repo_path: str):
        # 1. Parse all files with Tree-sitter
        entities = self.parse_repository(repo_path)
        
        # 2. Batch insert nodes (optimized transactions)
        self.batch_insert_nodes(entities)
        
        # 3. Extract relationships
        relationships = self.extract_relationships(entities)
        
        # 4. Batch insert edges
        self.batch_insert_edges(relationships)
        
        # 5. Compute derived metrics (complexity scores, blast radius)
        self.compute_analytics()
        
        # 6. Detect architecture risks
        self.detect_risks()
    
    def detect_changes(self, commit_hash: str):
        # Git diff → changed files
        # Re-parse only changed files
        # Incremental graph update (remove old → insert new)
        # Re-compute blast radius for affected edges
```

**Performance Targets:**
- 2,900-file project: re-index in <2 seconds
- 10,000-file project: <10 seconds
- Incremental updates: 100-1000 files in <500ms

---

### Phase 3: Vector Database for Semantic Search (Weeks 3-4)

#### 3.1 Vector DB Selection

**Recommended: Chroma (Apache 2.0, prototyping-focused)**
- Fastest setup time (<5 minutes)
- In-memory or persistent storage
- Built-in metadata filtering
- Scales to ~10M vectors (sufficient for most codebases)

**Alternative: Milvus (production scale)**
- Distributed architecture
- Handles 100M+ vectors
- More operational overhead

**Setup:**
```bash
# Chroma (Python)
pip install chromadb

# Or Docker (persistent storage)
docker run -d --name chroma -p 8000:8000 ghcr.io/chroma-core/chroma:latest
```

#### 3.2 Embedding Strategy

**Models (100% free, open-source):**
- **BGE-M3** (best multi-lingual, 384-dim)
- **MiniLM-L6-v2** (smallest, fastest, 384-dim)
- **bge-small-en-v1.5** (balanced, 384-dim)

**Code Chunking:**
```python
class CodeChunker:
    def chunk_by_ast(self, entity: CodeEntity):
        """AST-aware semantic chunking"""
        # Preserve syntactic units: entire functions, methods, classes
        # NOT random tokens (preserves meaning)
        # Example: function definition (signature + body) = 1 chunk
        pass
    
    def enrich_chunk(self, chunk: str, entity: CodeEntity):
        """Add metadata for semantic search"""
        return {
            "text": chunk,
            "embedding": self.embed_model.encode(chunk),
            "metadata": {
                "entity_id": entity.id,
                "entity_type": entity.type,
                "file_path": entity.file_path,
                "language": entity.language,
                "complexity": entity.complexity_metrics["cyclomatic_complexity"],
                "tags": self.extract_tags(chunk),  # security keywords, frameworks, etc.
            }
        }
```

**Embeddings Pipeline:**
```python
from sentence_transformers import SentenceTransformer
import chromadb

# 1. Initialize vector DB
client = chromadb.PersistentClient(path="/data/chroma")
collection = client.get_or_create_collection(
    name="codebase_embeddings",
    metadata={"hnsw:space": "cosine"}
)

# 2. Load embedding model
model = SentenceTransformer("BAAI/bge-small-en-v1.5")

# 3. Embed code chunks
for entity in code_entities:
    chunks = chunker.chunk_by_ast(entity)
    embeddings = model.encode([c["text"] for c in chunks])
    
    # 4. Insert into vector DB
    collection.upsert(
        ids=[c["metadata"]["entity_id"] for c in chunks],
        embeddings=embeddings,
        documents=[c["text"] for c in chunks],
        metadatas=[c["metadata"] for c in chunks]
    )
```

---

## Part II: Advanced Features

### Phase 4: Risk Detection & Architecture Analysis (Weeks 5-7)

#### 4.1 Architectural Risk Scoring

**Risk Categories:**
```python
class ArchitectureRisk:
    # Circular dependencies
    def detect_circular_deps(self):
        """Query graph: find cycles"""
        cypher = """
        MATCH (a:Module)-[*]->(a)
        RETURN a.name, length(path)
        """
        # Risk Score: 80/100 (high coupling)
    
    # God objects (classes with too many methods)
    def detect_god_objects(self):
        cypher = """
        MATCH (c:Class)-[:CONTAINS]->(m:Function)
        WITH c, count(m) as method_count
        WHERE method_count > 20
        RETURN c.name, method_count
        """
        # Risk Score: 70/100
    
    # Dead code (functions never called)
    def detect_dead_code(self):
        cypher = """
        MATCH (f:Function)
        WHERE NOT (f)<-[:CALLS]-()
        RETURN f.name, f.file_path
        """
        # Risk Score: 50/100
    
    # Dependency bloat (external imports > threshold)
    def detect_dependency_bloat(self):
        cypher = """
        MATCH (f:File)-[:IMPORTS]->(d:ExternalDependency)
        WITH f, count(d) as dep_count
        WHERE dep_count > 50
        RETURN f.path, dep_count
        """
        # Risk Score: 60/100
    
    # High blast radius (functions affecting many downstream)
    def detect_blast_radius(self, function_id: str):
        cypher = """
        MATCH (f:Function {id: $id})-[:CALLS*]->(downstream)
        RETURN count(DISTINCT downstream) as impact_count
        """
        # Risk Score: dynamic based on impact_count
```

**Risk Scoring Engine:**
```python
class RiskScorer:
    WEIGHTS = {
        "circular_dependency": 0.25,
        "high_complexity": 0.20,
        "large_blast_radius": 0.20,
        "dead_code": 0.15,
        "external_dependency_count": 0.10,
        "test_coverage": 0.10,  # lower = higher risk
    }
    
    def score_function(self, entity_id: str) -> float:
        """0-100 risk score"""
        scores = {
            "circular_dependency": self.is_in_cycle(entity_id) * 100,
            "high_complexity": min(entity.cyclomatic_complexity / 10 * 100, 100),
            "large_blast_radius": self.blast_radius_score(entity_id),
            "dead_code": 100 if not self.is_called(entity_id) else 0,
            "external_dependency_count": min(entity.dep_count / 20 * 100, 100),
            "test_coverage": 100 - (test_coverage_pct or 0),
        }
        return sum(scores[k] * self.WEIGHTS[k] for k in scores)
```

#### 4.2 Change Impact Analysis

**Multi-Hop Dependency Tracking:**
```python
class ImpactAnalyzer:
    def analyze_change_impact(self, changed_file: str, depth: int = 5):
        """Blast radius: what breaks if this file changes?"""
        
        cypher = f"""
        MATCH (f:File {{path: $file_path}})
        MATCH p = (f)-[r:CALLS|IMPORTS|INHERITS*..{depth}]->(affected)
        WHERE affected.type IN ['Function', 'Class', 'Module']
        RETURN 
            affected.name,
            affected.file_path,
            length(p) as hops,
            [rel in relationships(p) | type(rel)] as relationship_chain
        ORDER BY hops ASC
        """
        
        results = self.graph.execute(cypher, {"file_path": changed_file})
        
        impact_report = {
            "direct_dependents": filter(results, lambda r: r['hops'] == 1),
            "transitive_dependents": filter(results, lambda r: r['hops'] > 1),
            "affected_test_files": self.find_tests(results),
            "estimated_risk": self.compute_risk_score(results),
        }
        
        return impact_report
```

#### 4.3 Ownership & Test Coverage Tracking

**Code Ownership from Git:**
```python
import subprocess

class OwnershipMapper:
    def map_code_ownership(self, repo_path: str):
        """Blame analysis: who last touched each entity?"""
        
        for file_path in self.all_code_files:
            # git blame → commits → authors
            blame = subprocess.run(
                ["git", "blame", "-p", file_path],
                capture_output=True, text=True
            )
            
            for line, author, commit_date in parse_blame(blame):
                # Link code entity to author/timestamp
                cypher = """
                MATCH (f:Function {file_path: $file, line_start: $line})
                SET f.last_author = $author, f.last_modified = $date
                """
                self.graph.execute(cypher, {
                    "file": file_path,
                    "line": line,
                    "author": author,
                    "date": commit_date,
                })
```

**Test Coverage Tracking:**
```python
class TestCoverageMapper:
    def map_test_coverage(self, coverage_report: dict):
        """Coverage report (pytest, go test, etc.) → graph"""
        
        for function_id, coverage_pct in coverage_report.items():
            cypher = """
            MATCH (f:Function {id: $id})
            SET f.test_coverage = $coverage
            MERGE (f)-[:COVERED_BY]->(t:TestFile {path: $test_file})
            """
            self.graph.execute(cypher, {
                "id": function_id,
                "coverage": coverage_pct,
                "test_file": coverage_report[function_id]["test_file"],
            })
```

---

### Phase 5: Natural Language Query Engine (Weeks 6-9)

#### 5.1 Semantic + Structural Retrieval (Hybrid RAG)

**Architecture:**
```
User Question
    ↓
1. Query Router (which search strategy?)
    ├─ Structural Graph Search (multi-hop queries)
    │   └─ "Find all functions that call database.update()"
    └─ Semantic Vector Search (concept matching)
        └─ "Which functions handle authentication?"
    ↓
2. Retrieve Relevant Context
    ├─ Graph: traverse relationships (5-hop limit)
    └─ Vector DB: top-K semantic matches (K=10)
    ↓
3. Merge Results (dedup, rank by relevance)
    ↓
4. LLM Context Assembly
    └─ Only most relevant code chunks + metadata
    ↓
5. LLM Generation (Ollama local model)
    └─ Answer with code citations
```

**Query Router Implementation:**
```python
class QueryRouter:
    def route_query(self, user_question: str) -> str:
        """Determine search strategy"""
        
        structural_keywords = {
            "calls", "imports", "inherits", "dependencies",
            "references", "uses", "depends", "affected"
        }
        
        if any(kw in user_question.lower() for kw in structural_keywords):
            return "structural"  # Graph traversal
        else:
            return "semantic"    # Vector similarity

class HybridRetriever:
    def retrieve(self, question: str, strategy: str):
        if strategy == "structural":
            return self.structural_search(question)
        else:
            return self.semantic_search(question)
    
    def structural_search(self, question: str) -> list:
        """Parse question → Cypher query"""
        # Examples:
        # "Find functions that call database.update()"
        # → MATCH (f:Function)-[:CALLS]->(target:Function {name: 'update'})
        #   WHERE target.module = 'database'
        # → RETURN f
        
        # Use LLM to convert English → Cypher
        cypher_query = self.llm.generate_cypher(question)
        results = self.graph.execute(cypher_query)
        return results
    
    def semantic_search(self, question: str) -> list:
        """Embed question → vector search"""
        question_embedding = self.embedding_model.encode(question)
        results = self.vector_db.search(
            query_embedding=question_embedding,
            top_k=10,
            filters={"language": "python"}  # optional
        )
        return results
```

#### 5.2 LLM-to-Cypher Translation

**In-Context Learning for Query Generation:**
```python
class LLMQueryGenerator:
    CYPHER_EXAMPLES = """
Examples:
1. Q: "Find all functions that call database.update()"
   A: MATCH (f:Function)-[:CALLS]->(target:Function {name: 'update'})
      WHERE target.module = 'database'
      RETURN f.name, f.file_path

2. Q: "Which classes inherit from BaseController?"
   A: MATCH (c:Class)-[:INHERITS_FROM]->(base:Class {name: 'BaseController'})
      RETURN c.name

3. Q: "What's the blast radius if we change the auth.py file?"
   A: MATCH (f:File {path: 'auth.py'})-[:CONTAINS]->(entity)
      MATCH (entity)-[:CALLS*..3]->(downstream)
      RETURN COUNT(DISTINCT downstream)
"""
    
    def generate_cypher(self, question: str) -> str:
        prompt = f"""You are a graph query expert. Convert this question to Cypher.
{self.CYPHER_EXAMPLES}

Question: {question}
Answer (Cypher only):"""
        
        cypher = self.llm.generate(prompt, max_tokens=200)
        return cypher.strip()
```

#### 5.3 Answer Generation Pipeline

```python
class AnswerGenerator:
    def generate_answer(self, question: str, context: list):
        """LLM generates final answer with citations"""
        
        context_str = "\n---\n".join([
            f"File: {c['file_path']}\n"
            f"Entity: {c['entity_name']}\n"
            f"Code:\n{c['code_snippet']}\n"
            f"Complexity: {c['complexity']}"
            for c in context
        ])
        
        prompt = f"""Based on the codebase context below, answer this question:
Q: {question}

Context:
{context_str}

Provide:
1. Direct answer
2. Code citations (file:line or entity ID)
3. Architectural insights
4. Risks or concerns (if relevant)

Answer:"""
        
        answer = self.ollama_client.generate(prompt)
        return answer
```

---

### Phase 6: LLM Integration (Weeks 8-10)

#### 6.1 Local Ollama Setup

**Installation:**
```bash
# macOS/Linux/Windows from ollama.com
curl https://ollama.ai/install.sh | sh

# Or Docker (recommended for production)
docker run -d --name ollama -p 11434:11434 \
  --gpus all \
  ollama/ollama

# Pull a coding-optimized model
ollama pull mistral    # 7B, fast, good reasoning
ollama pull neural-chat  # 7B, conversation-tuned
ollama pull codellama  # 34B, code-specialized (needs 24GB VRAM)
```

**Model Selection for Codebase Analysis:**
| Model | Size | Speed | Cost | Best For |
|-------|------|-------|------|----------|
| Mistral 7B | 4GB | Fast | Free | General queries, Cypher generation |
| Neural-Chat 7B | 4GB | Fast | Free | Conversational explanation |
| CodeLlama 13B | 7GB | Medium | Free | Code generation, fixes |
| Llama 2 70B | 40GB | Slow | Free | Complex reasoning |

**Recommendation for MVP:** Mistral 7B (best speed/quality tradeoff)

#### 6.2 Context Window Optimization

**Problem:** LLM context windows (4K-8K tokens) are tiny vs. codebase sizes.

**Solution: Retrieval-Augmented Generation (RAG)**
```python
class ContextOptimizer:
    def assemble_minimal_context(self, question: str, max_tokens: int = 4000):
        """Retrieve ONLY relevant code for LLM context"""
        
        # 1. Hybrid retrieval (structural + semantic)
        graph_results = self.hybrid_retriever.retrieve(question)
        
        # 2. Rank by relevance
        ranked = self.rank_by_relevance(graph_results, question)
        
        # 3. Greedily pack context (stop at max_tokens)
        context = []
        token_count = 0
        for item in ranked:
            tokens = len(item["code"].split()) * 1.3  # rough estimate
            if token_count + tokens > max_tokens:
                break
            context.append(item)
            token_count += tokens
        
        return context
    
    def rank_by_relevance(self, results: list, question: str):
        """Score results by relevance to question"""
        
        # Multi-factor ranking
        for result in results:
            score = (
                0.4 * self.semantic_similarity(question, result["docstring"]) +
                0.3 * self.is_directly_mentioned(question, result["name"]) +
                0.2 * (1 / (result.get("hops", 1) + 1)) +  # prefer direct deps
                0.1 * (1 - result.get("cyclomatic_complexity", 0) / 100)  # simpler=better
            )
            result["relevance_score"] = score
        
        return sorted(results, key=lambda x: x["relevance_score"], reverse=True)
```

**Token Accounting:**
```python
def count_tokens(text: str) -> int:
    """Rough token estimate (Llama tokenizer)"""
    return len(text.split()) * 1.3  # 1 token ≈ 0.75 words

# Example: 4K token limit
# - System prompt: 200 tokens
# - User question: 100 tokens
# - Code context: 3,000 tokens (available)
# - Reasoning buffer: 700 tokens
```

#### 6.3 LLM API Integration

```python
import requests

class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
    
    def generate(self, prompt: str, model: str = "mistral") -> str:
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "temperature": 0.3,  # low temp = deterministic
                "top_p": 0.9,
                "stream": False,
            },
            timeout=120
        )
        return response.json()["response"]
    
    def streaming_generate(self, prompt: str, model: str = "mistral"):
        """For long-running queries"""
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": True},
            stream=True
        )
        for line in response.iter_lines():
            if line:
                yield json.loads(line)["response"]
```

---

## Part III: Platform & Operations

### Phase 7: FastAPI Backend (Weeks 10-11)

#### 7.1 API Endpoints

```python
from fastapi import FastAPI, BackgroundTasks
from typing import Optional

app = FastAPI(title="Codebase Intelligence API")

@app.post("/analyze/repository")
async def analyze_repository(
    repo_url: str,
    background_tasks: BackgroundTasks
):
    """Ingest new repository"""
    background_tasks.add_task(ingest_codebase, repo_url)
    return {"status": "queued", "repo": repo_url}

@app.get("/query")
async def query_codebase(
    question: str,
    search_strategy: Optional[str] = "hybrid"  # or "structural", "semantic"
):
    """Natural language query"""
    context = retriever.retrieve(question, strategy=search_strategy)
    answer = llm_generator.generate_answer(question, context)
    return {
        "question": question,
        "answer": answer,
        "sources": [c["file_path"] for c in context],
        "confidence": calculate_confidence(answer)
    }

@app.get("/impact/{file_path:path}")
async def impact_analysis(file_path: str, depth: int = 5):
    """Blast radius analysis"""
    impact = impact_analyzer.analyze_change_impact(file_path, depth)
    return impact

@app.get("/risks")
async def list_architecture_risks(
    min_severity: str = "medium",  # low, medium, high, critical
    limit: int = 50
):
    """Top architecture risks"""
    risks = risk_detector.get_risks(min_severity, limit)
    return {
        "total_risks": len(risks),
        "critical": [r for r in risks if r["severity"] == "critical"],
        "high": [r for r in risks if r["severity"] == "high"],
        "risks": risks[:limit]
    }

@app.get("/function/{function_id}")
async def get_function_details(function_id: str):
    """Detailed function profile"""
    return {
        "details": graph_db.get_node(function_id),
        "callers": graph_db.get_incoming_calls(function_id),
        "callees": graph_db.get_outgoing_calls(function_id),
        "test_coverage": graph_db.get_test_coverage(function_id),
        "risk_score": risk_scorer.score_function(function_id),
    }

@app.get("/stats")
async def codebase_statistics():
    """Summary statistics"""
    return {
        "total_functions": graph_db.count_nodes("Function"),
        "total_classes": graph_db.count_nodes("Class"),
        "total_files": graph_db.count_nodes("File"),
        "languages": graph_db.get_language_distribution(),
        "avg_complexity": graph_db.compute_avg_complexity(),
        "total_lines_of_code": graph_db.sum_property("lines_of_code"),
        "architectural_risks": risk_detector.count_risks(),
    }
```

#### 7.2 Background Job Processing

```python
from celery import Celery
import logging

celery_app = Celery("codebase_intelligence")
logger = logging.getLogger(__name__)

@celery_app.task(name="ingest_codebase")
def ingest_codebase(repo_url: str):
    """Long-running repository analysis"""
    logger.info(f"Starting ingestion: {repo_url}")
    
    try:
        # 1. Clone/pull repo
        repo_path = clone_or_pull_repo(repo_url)
        
        # 2. Parse codebase
        entities = parser.parse_repository(repo_path)
        logger.info(f"Parsed {len(entities)} entities")
        
        # 3. Build knowledge graph
        graph_builder.ingest_codebase(repo_path, entities)
        logger.info("Graph ingestion complete")
        
        # 4. Compute analytics
        risk_detector.detect_all_risks()
        logger.info("Risk analysis complete")
        
        # 5. Store embeddings
        vector_db_builder.embed_and_store(entities)
        logger.info("Embeddings stored")
        
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        raise

@celery_app.task(name="incremental_update")
def incremental_update(repo_url: str, commit_hash: str):
    """Update graph for new commit"""
    changed_files = get_changed_files(repo_url, commit_hash)
    for file_path in changed_files:
        # Re-parse changed file
        entities = parser.parse_file(file_path)
        # Remove old nodes/edges
        graph_db.delete_entities_for_file(file_path)
        # Insert new
        graph_builder.ingest_entities(entities)
```

---

### Phase 8: Web Frontend (Weeks 11-13)

#### 8.1 React/Next.js Dashboard

**Tech Stack:**
- Next.js 14 (full-stack React)
- TailwindCSS (styling)
- Recharts (graph visualizations)
- Plotly (interactive code dependency graphs)

**Core Pages:**

**1. Dashboard (Overview)**
```typescript
// pages/dashboard.tsx
export default function Dashboard() {
  return (
    <div>
      <h1>Codebase Intelligence Dashboard</h1>
      
      <StatsGrid>
        <StatCard title="Total Functions" value={stats.functions} />
        <StatCard title="Avg Complexity" value={stats.complexity} />
        <StatCard title="Critical Risks" value={stats.critical_risks} />
      </StatsGrid>
      
      <LanguageDistribution data={stats.languages} />
      <TopRisks risks={stats.top_risks} />
    </div>
  )
}
```

**2. Query Interface**
```typescript
// pages/query.tsx
export default function QueryPage() {
  const [question, setQuestion] = useState("")
  const [results, setResults] = useState(null)
  
  const handleQuery = async () => {
    const res = await fetch(`/api/query?question=${encodeURIComponent(question)}`)
    setResults(await res.json())
  }
  
  return (
    <div>
      <SearchBox onSubmit={handleQuery} />
      {results && <AnswerDisplay results={results} />}
    </div>
  )
}
```

**3. Impact Analysis**
```typescript
// pages/impact/[filePath].tsx
export default function ImpactAnalysis({ filePath }) {
  const [impact, setImpact] = useState(null)
  
  useEffect(() => {
    fetch(`/api/impact/${filePath}`).then(r => r.json()).then(setImpact)
  }, [filePath])
  
  return (
    <div>
      <h1>Blast Radius: {filePath}</h1>
      <BlastRadiusVisualization impact={impact} />
      <AffectedTestsList tests={impact.affected_tests} />
    </div>
  )
}
```

**4. Code Graph Explorer** (interactive D3.js visualization)
```typescript
// components/CodeGraphVisualizer.tsx
import * as d3 from "d3"

export function CodeGraphVisualizer({ graphData }) {
  useEffect(() => {
    const svg = d3.select("#graph-container")
    const simulation = d3.forceSimulation(graphData.nodes)
      .force("link", d3.forceLink(graphData.edges).id(d => d.id))
      .force("charge", d3.forceManyBody())
    
    // Render nodes & edges
  }, [graphData])
  
  return <div id="graph-container" style={{height: "800px"}} />
}
```

---

### Phase 9: Docker & Deployment (Weeks 12-14)

#### 9.1 Docker Compose Stack

```yaml
version: '3.8'

services:
  # Graph Database
  arcadedb:
    image: arcadedb/arcadedb:latest
    ports:
      - "2480:2480"  # HTTP
      - "2424:2424"  # Binary
    environment:
      JAVA_OPTS: "-Xmx2g"
    volumes:
      - arcadedb_data:/data
  
  # Vector Database
  chroma:
    image: ghcr.io/chroma-core/chroma:latest
    ports:
      - "8000:8000"
    volumes:
      - chroma_data:/data
  
  # LLM (Ollama)
  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    environment:
      OLLAMA_NUM_PARALLEL: 2
    volumes:
      - ollama_models:/root/.ollama
    # GPU support
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
  
  # FastAPI Backend
  backend:
    build: ./backend
    ports:
      - "8001:8000"
    environment:
      GRAPH_DB_URL: "http://arcadedb:2480"
      VECTOR_DB_URL: "http://chroma:8000"
      OLLAMA_BASE_URL: "http://ollama:11434"
    depends_on:
      - arcadedb
      - chroma
      - ollama
  
  # Redis (task queue)
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  
  # Celery Worker
  celery_worker:
    build: ./backend
    command: celery -A celery_app worker -l info
    environment:
      GRAPH_DB_URL: "http://arcadedb:2480"
      REDIS_URL: "redis://redis:6379"
    depends_on:
      - arcadedb
      - redis
  
  # React Frontend
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: "http://localhost:8001"

volumes:
  arcadedb_data:
  chroma_data:
  ollama_models:
```

**Run:**
```bash
docker-compose up -d
# Visit http://localhost:3000
```

#### 9.2 Deployment Options

**Option 1: Local Machine**
- Needs: 16GB RAM, GPU optional (16GB VRAM for large LLMs)
- Setup: `docker-compose up`

**Option 2: Cloud VPS (Recommended for free tier)**
- Provider: Hetzner, Linode, DigitalOcean
- Instance: 8GB RAM, 4 vCPU, $20-40/month
- No GPU (use smaller quantized models)

**Option 3: Free-tier cloud**
- Render.com: 1 free instance (0.5GB RAM) — too small
- Railway.app: $5/month baseline
- Fly.io: free tier available

---

## Part IV: Advanced Features & Optimization

### Phase 10: Multi-Agent Orchestration (Weeks 15-17)

#### 10.1 Agentic Framework

```python
from langchain.agents import Tool, AgentExecutor, initialize_agent
from langchain.llms.ollama import Ollama

# Define tools
tools = [
    Tool(
        name="code_search",
        func=hybrid_retriever.retrieve,
        description="Search codebase by function name, pattern, or concept"
    ),
    Tool(
        name="impact_analysis",
        func=impact_analyzer.analyze_change_impact,
        description="Analyze blast radius of code changes"
    ),
    Tool(
        name="risk_detection",
        func=risk_detector.scan_for_risks,
        description="Scan codebase for architectural risks"
    ),
    Tool(
        name="test_generation",
        func=test_generator.generate_tests,
        description="Generate unit tests for a function"
    ),
]

# Initialize agent
llm = Ollama(model="mistral")
agent = initialize_agent(
    tools,
    llm,
    agent="zero-shot-react-description",
    verbose=True
)

# Example: Multi-step task
result = agent.run(
    "Find all functions that access the database, analyze their risks, "
    "and generate tests for high-risk functions."
)
```

#### 10.2 Refactoring Recommendation Engine

```python
class RefactoringRecommender:
    def recommend_refactorings(self, codebase_analysis: dict):
        """Generate refactoring plans"""
        
        recommendations = []
        
        # 1. Break up God Objects
        for god_class in codebase_analysis["god_objects"]:
            recommendation = {
                "type": "extract_methods",
                "target": god_class,
                "severity": "high",
                "suggestion": f"Split {god_class} into {god_class}Manager + {god_class}Handler",
                "estimated_impact": "High — improves testability, reduces coupling",
            }
            recommendations.append(recommendation)
        
        # 2. Remove dead code
        for dead_func in codebase_analysis["dead_code"]:
            recommendations.append({
                "type": "remove_dead_code",
                "target": dead_func,
                "severity": "medium",
                "suggestion": f"Remove {dead_func} — never called",
            })
        
        # 3. Break circular dependencies
        for cycle in codebase_analysis["circular_deps"]:
            recommendations.append({
                "type": "break_cycle",
                "target": cycle,
                "severity": "high",
                "suggestion": f"Introduce mediator pattern to break: {' → '.join(cycle)}",
            })
        
        return recommendations
```

---

### Phase 11: Security & Compliance Scanning (Weeks 18-19)

#### 11.1 SAST Integration

```python
class SecurityScanner:
    RULES = {
        "sql_injection": {
            "pattern": r"query.*\+.*user_input",
            "severity": "critical",
            "description": "Potential SQL injection",
        },
        "hardcoded_secrets": {
            "pattern": r'(password|secret|api_key)\s*=\s*["\'][^"\']*["\']',
            "severity": "critical",
            "description": "Hardcoded credentials",
        },
        "insecure_crypto": {
            "pattern": r"MD5|SHA1|DES",
            "severity": "high",
            "description": "Insecure cryptographic algorithm",
        },
    }
    
    def scan(self, codebase_path: str):
        """Static security scan"""
        issues = []
        
        for file_path in walk_files(codebase_path):
            content = read_file(file_path)
            
            for rule_name, rule in self.RULES.items():
                matches = re.finditer(rule["pattern"], content)
                for match in matches:
                    issues.append({
                        "file": file_path,
                        "line": get_line_number(content, match.start()),
                        "rule": rule_name,
                        "severity": rule["severity"],
                        "message": rule["description"],
                        "code_snippet": extract_context(content, match),
                    })
        
        return issues
```

---

## Part V: Monitoring & Iteration

### Phase 12: Observability & Analytics (Weeks 20-21)

#### 12.1 Metrics & Logging

```python
from prometheus_client import Counter, Histogram, Gauge
import logging

# Prometheus metrics
query_latency = Histogram("query_latency_seconds", "API query latency")
graph_ingestion_duration = Histogram("graph_ingestion_seconds", "Graph build time")
llm_token_usage = Counter("llm_tokens_total", "LLM tokens consumed")
retrieval_recall = Gauge("retrieval_recall", "RAG retrieval recall@10")

# Logging
logger = logging.getLogger("codebase_intelligence")
logger.addHandler(logging.FileHandler("logs/app.log"))
logger.addHandler(logging.handlers.RotatingFileHandler("logs/app.log", maxBytes=10MB))
```

#### 12.2 Dashboard Queries

```python
# Grafana queries (Prometheus)
# Query latency p95
histogram_quantile(0.95, query_latency_seconds)

# Graph ingestion trend
rate(graph_ingestion_seconds_bucket[1h])

# LLM cost estimation
llm_tokens_total * 0.002  # assuming $2 per million tokens (Ollama = free)
```

---

## Part VI: Testing & Quality

### Phase 13: Testing Strategy (Weeks 22-23)

#### 13.1 Unit Tests

```python
import pytest

class TestASTParser:
    def test_parse_python_function(self):
        code = """
def add(a, b):
    return a + b
"""
        entities = parser.parse_code(code, "python")
        assert len(entities) == 1
        assert entities[0].name == "add"
        assert entities[0].type == "function"
    
    def test_extract_function_calls(self):
        code = """
def foo():
    bar()
    baz()
"""
        entities = parser.parse_code(code, "python")
        relationships = parser.extract_relationships(code)
        assert len(relationships) == 2
        assert all(r.type == "calls" for r in relationships)

class TestGraphBuilder:
    def test_ingest_entities(self):
        entities = [MockEntity(...), MockEntity(...)]
        graph_builder.ingest_entities(entities)
        assert graph_db.count_nodes("Function") == 2
    
    def test_relationship_creation(self):
        # Verify edges are correctly created
        pass

class TestQueryEngine:
    def test_semantic_search(self):
        results = retriever.semantic_search("authentication")
        assert all("auth" in r["docstring"].lower() for r in results)
    
    def test_structural_query(self):
        results = retriever.structural_search("functions called by login()")
        assert all(callable in results for callable in [...])

class TestLLMIntegration:
    def test_answer_generation(self):
        question = "What functions handle database access?"
        answer = llm_generator.generate_answer(question, mock_context)
        assert len(answer) > 0
        assert "database" in answer.lower()
```

#### 13.2 Integration Tests

```python
@pytest.mark.integration
class TestEndToEnd:
    def test_full_pipeline(self, sample_repo):
        # 1. Ingest repo
        graph_builder.ingest_codebase(sample_repo)
        
        # 2. Query
        results = retriever.retrieve("Find functions using SQL")
        assert len(results) > 0
        
        # 3. Generate answer
        answer = llm_generator.generate_answer("...", results)
        assert answer is not None
```

---

## Timeline & Milestones

| Week | Phase | Deliverable |
|------|-------|-------------|
| 1-2 | AST Parser | Multi-language code extraction |
| 2-4 | Graph DB | ArcadeDB schema + ingestion |
| 3-4 | Vector DB | Chroma + embeddings pipeline |
| 5-7 | Risk Detection | Architectural risk scoring |
| 6-9 | Query Engine | Hybrid (structural + semantic) RAG |
| 8-10 | LLM Integration | Ollama + Mistral/CodeLlama |
| 10-11 | FastAPI | Production backend + Celery jobs |
| 11-13 | Frontend | Next.js dashboard + visualizations |
| 12-14 | Docker | Compose stack + deployment |
| 15-17 | Multi-Agent | Agentic refactoring recommendations |
| 18-19 | Security | SAST + compliance scanning |
| 20-21 | Monitoring | Prometheus + Grafana |
| 22-23 | Testing | Unit + integration test coverage |
| 24+ | Optimization | Performance tuning + scaling |

---

## Resource Requirements

### Hardware (Minimum)
- **CPU:** 4 cores
- **RAM:** 16GB (8GB minimum for Ollama + Chroma)
- **Storage:** 100GB (SSD recommended)
- **GPU:** Optional (16GB VRAM accelerates Ollama inference 10-20x)

### Hardware (Recommended for Production)
- **CPU:** 8+ cores
- **RAM:** 32GB
- **Storage:** 500GB NVMe
- **GPU:** RTX 4060 Ti or better (12GB+ VRAM)

### Free/Open-Source Budget
- **Graph DB:** $0 (ArcadeDB Apache 2.0)
- **Vector DB:** $0 (Chroma Apache 2.0)
- **LLM:** $0 (Ollama + local models)
- **Backend:** $0 (FastAPI + Python)
- **Frontend:** $0 (Next.js + Node.js)
- **Hosting:** $20-50/month (VPS with GPU)
- **Total First Year:** ~$600-1000 (infrastructure only)

---

## GitHub Repository Structure

```
enterprise-codebase-intelligence/
├── backend/
│   ├── ast_parser/
│   │   ├── tree_sitter_wrapper.py
│   │   ├── language_parsers.py
│   │   └── symbol_resolver.py
│   ├── graph_db/
│   │   ├── arcade_client.py
│   │   ├── schema.py
│   │   └── builders.py
│   ├── vector_db/
│   │   ├── chroma_client.py
│   │   ├── embeddings.py
│   │   └── chunking.py
│   ├── retrieval/
│   │   ├── hybrid_retriever.py
│   │   ├── query_router.py
│   │   └── llm_to_cypher.py
│   ├── llm/
│   │   ├── ollama_client.py
│   │   └── answer_generator.py
│   ├── risk_detection/
│   │   ├── risk_scorer.py
│   │   └── rules.py
│   ├── api/
│   │   └── main.py
│   └── requirements.txt
├── frontend/
│   ├── pages/
│   │   ├── dashboard.tsx
│   │   ├── query.tsx
│   │   └── impact/[filePath].tsx
│   ├── components/
│   │   ├── CodeGraphVisualizer.tsx
│   │   └── QueryBox.tsx
│   └── package.json
├── docker-compose.yml
├── README.md
└── ROADMAP.md (this file)
```

---

## Success Metrics

- **Query Latency:** <2 seconds (p95)
- **Index Time:** <10 seconds per 1000 files
- **Retrieval Recall:** >80% (top-10 results contain relevant code)
- **LLM Answer Quality:** >75% (manual evaluation)
- **Architecture Risk Detection:** >90% recall on common patterns
- **Blast Radius Accuracy:** >85% (vs. manual code review)

---

## Future Enhancements (Post-MVP)

1. **IDE Plugins** — VSCode/IntelliJ integration
2. **Git Hooks** — Pre-commit impact analysis
3. **Distributed Graphs** — Scale to 100M+ nodes (sharding)
4. **Fine-tuned Models** — CodeLlama fine-tuned on codebase
5. **Visualization** — Interactive 3D dependency graphs
6. **ML-based Risk** — Anomaly detection on code patterns
7. **Automated Fixes** — AI-generated refactoring patches
8. **Time-travel Analysis** — Historical code evolution tracking

---

## Conclusion

This roadmap provides a **turnkey, open-source alternative to proprietary tools** (Snyk, Codacy, GitHub Advanced Security) with **100% free infrastructure cost** for small-to-medium codebases.

Key advantages:
✅ Fully self-hosted (data privacy)
✅ Zero licensing costs
✅ Extendable architecture
✅ Multi-language support
✅ Production-ready (24+ weeks → launch)

**Start with Phase 1-6 (AST + Graph + RAG) for MVP. Phases 7-13 add polish, security, and scale.**

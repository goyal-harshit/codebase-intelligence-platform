import axios from "axios";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const api = axios.create({ baseURL: API_URL });

/* ---- Auth token storage + injection ---- */

const TOKEN_KEY = "ci_auth_token";

export const getToken = (): string | null =>
  typeof window === "undefined" ? null : window.localStorage.getItem(TOKEN_KEY);

export const setToken = (token: string | null) => {
  if (typeof window === "undefined") return;
  if (token) window.localStorage.setItem(TOKEN_KEY, token);
  else window.localStorage.removeItem(TOKEN_KEY);
};

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/* ---- Check live backend reachability ---- */
export const checkBackendHealth = async (): Promise<boolean> => {
  try {
    const res = await api.get("/api/v1/stats", { timeout: 3000 });
    return res.status === 200;
  } catch {
    return false;
  }
};

/* ---- Helper to return fallback mock data when API is unreachable ---- */

async function withFallback<T>(promise: Promise<T>, fallback: T): Promise<T> {
  try {
    return await promise;
  } catch (error) {
    console.warn("Backend API unreachable, using sample mock data for preview:", error);
    return fallback;
  }
}

/* ---- Interfaces ---- */

export interface Stats {
  total_files: number;
  total_functions: number;
  total_classes: number;
  total_calls: number;
}

export interface Risk {
  type: string;
  severity: string;
  target: string;
  file: string;
  details: string;
}

export interface QueryResult {
  question: string;
  strategy: string;
  answer: string;
  sources: string[];
  cypher?: string | null;
}

export interface Affected {
  name: string;
  file: string;
  hops: number;
}

export interface ImpactResult {
  target: string;
  directly_affected_count: number;
  transitively_affected_count: number;
  directly_affected: Affected[];
  transitively_affected: Affected[];
  risk_level: string;
}

export interface IngestJob {
  job_id: string;
  user_id?: string | null;
  status: string;
  step?: string | null;
  progress?: number | null;
  error?: string | null;
  result?: Record<string, unknown> | null;
  warnings?: string[];
  repo_url?: string | null;
  repo_path?: string | null;
  stale?: boolean;
}

export interface Hotspot {
  file: string;
  churn: number;
  total_complexity: number;
  max_complexity: number;
  functions: number;
  lines_of_code: number;
  score: number;
}

export interface HotspotResult {
  available: boolean;
  mode?: "churn_x_complexity" | "complexity_only";
  reason?: string;
  repo_path?: string;
  hotspots: Hotspot[];
  total?: number;
}

export interface NotificationItem {
  id: string;
  type: string;
  level: string;
  title: string;
  body?: string | null;
  detail?: Record<string, unknown> | null;
  read: boolean;
  created_at: string;
}

export interface SecurityFinding {
  rule: string;
  severity: string;
  file: string;
  line: number;
  message: string;
  snippet: string;
  source?: string;
}

export interface SecurityResult {
  available?: boolean;
  reason?: string;
  repo_path?: string;
  files_scanned?: number;
  findings: SecurityFinding[];
  total: number;
  by_severity: Record<string, number>;
}

export interface Recommendation {
  id: string;
  type: string;
  title: string;
  severity: string;
  target: string;
  file?: string | null;
  rationale: string;
  suggestion: string;
  effort: string;
  details?: string | null;
}

export interface RefactorResult {
  recommendations: Recommendation[];
  total: number;
  narrative?: string | null;
}

export interface RepoFiles {
  repo_path: string;
  count: number;
  files: string[];
  job_id?: string;
}

export interface ServiceStatus {
  ok: boolean;
  url?: string | null;
  model?: string | null;
  model_present?: boolean | null;
  error?: string;
}

export interface ServiceHealth {
  services: Record<string, ServiceStatus>;
  all_ok: boolean;
}

export interface LlmConfig {
  provider: string;
  base_url?: string | null;
  model?: string | null;
  api_key_set: boolean;
  source?: string;
}

export interface LlmModels {
  provider: string;
  available: boolean;
  models: string[];
  error?: string;
}

export interface LlmConfigUpdate {
  provider: string;
  base_url?: string | null;
  model?: string | null;
  api_key?: string | null;
}

export interface GraphifyNode {
  id: string;
  name: string;
  type: string;
  community: number;
  file?: string;
}

export interface GraphifyLink {
  source: string;
  target: string;
}

export interface GraphifyGraph {
  nodes: GraphifyNode[];
  links: GraphifyLink[];
  community_labels: Record<string, string>;
}

export interface GraphifyStats {
  nodes: number;
  edges: number;
  communities: number;
  available: boolean;
}

export interface Comment {
  id: string;
  target_type: string;
  target_id: string;
  user_id?: string | null;
  body: string;
  created_at: string;
  updated_at: string;
}

export interface ActivityEvent {
  id: number;
  user_id?: string | null;
  action: string;
  target?: string | null;
  detail?: Record<string, unknown> | null;
  created_at: string;
}

export interface AuthUser {
  id: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
  full_name?: string | null;
}

export interface DocgenPage {
  module: string;
  display?: string;
  markdown: string;
}

/* ---- Mock Fallback Datasets ---- */

const MOCK_STATS: Stats = {
  total_files: 48,
  total_functions: 312,
  total_classes: 42,
  total_calls: 1024,
};

const MOCK_RISKS: { risks: Risk[]; total: number } = {
  total: 5,
  risks: [
    {
      type: "circular_dependency",
      severity: "high",
      target: "backend/database/models.py",
      file: "backend/database/models.py",
      details: "Cycle detected between models.py and auth/service.py causing tight coupling.",
    },
    {
      type: "god_class",
      severity: "medium",
      target: "backend/api/routes_query.py:QueryEngine",
      file: "backend/api/routes_query.py",
      details: "Class QueryEngine handles routing, Cypher query generation, and LLM formatting with 640 lines.",
    },
    {
      type: "high_fan_out",
      severity: "medium",
      target: "backend/config/settings.py",
      file: "backend/config/settings.py",
      details: "Settings module is directly imported by 28 modules across the backend pipeline.",
    },
    {
      type: "deep_inheritance",
      severity: "low",
      target: "backend/services/base_worker.py:WorkerBase",
      file: "backend/services/base_worker.py",
      details: "Worker class hierarchy exceeds 4 levels of inheritance.",
    },
    {
      type: "unused_export",
      severity: "high",
      target: "backend/utils/legacy_parser.py:parse_v1",
      file: "backend/utils/legacy_parser.py",
      details: "Function parse_v1 has 0 internal or external caller invocations.",
    },
  ],
};

const MOCK_SECURITY: SecurityResult = {
  available: true,
  files_scanned: 48,
  total: 4,
  by_severity: { high: 1, medium: 2, low: 1 },
  findings: [
    {
      rule: "hardcoded_secret",
      severity: "high",
      file: "backend/config/defaults.py",
      line: 14,
      message: "Potential hardcoded JWT signing secret detected in fallback configuration.",
      snippet: 'SECRET_KEY = "dev_secret_change_me_in_prod"',
      source: "builtin",
    },
    {
      rule: "insecure_deserialization",
      severity: "medium",
      file: "backend/cache/redis_store.py",
      line: 88,
      message: "pickle.loads used on cached payloads without HMAC signature verification.",
      snippet: "data = pickle.loads(raw_bytes)",
      source: "bandit",
    },
    {
      rule: "sql_injection",
      severity: "medium",
      file: "backend/db/query_builder.py",
      line: 45,
      message: "Raw string formatting used in SQL query execution.",
      snippet: `cursor.execute(f"SELECT * FROM users WHERE username = '{user_input}'")`,
      source: "bandit",
    },
    {
      rule: "permissive_cors",
      severity: "low",
      file: "backend/main.py",
      line: 22,
      message: "Wildcard '*' allowed origins configured in FastAPI CORSMiddleware.",
      snippet: 'allow_origins=["*"]',
      source: "ruff",
    },
  ],
};

const MOCK_REFACTOR: RefactorResult = {
  total: 3,
  narrative: "Systemic refactoring plan focused on decoupling database models and reducing module complexity.",
  recommendations: [
    {
      id: "REC-01",
      type: "extract_module",
      title: "Decouple Circular Models & Auth",
      severity: "high",
      target: "backend/database/models.py",
      file: "backend/database/models.py",
      rationale: "Break cyclic import between models.py and auth/service.py by introducing an AuthUser DTO interface.",
      suggestion: "Move user authorization properties to backend/auth/dto.py.",
      effort: "Medium (2-3 hrs)",
      details: "Cycle causes lazy loading issues during Alembic database migrations.",
    },
    {
      id: "REC-02",
      type: "split_class",
      title: "Split QueryEngine God Class",
      severity: "medium",
      target: "backend/api/routes_query.py",
      file: "backend/api/routes_query.py",
      rationale: "Separate Cypher query construction from HTTP response formatting.",
      suggestion: "Extract CypherBuilder into backend/services/cypher.py.",
      effort: "Large (4-5 hrs)",
      details: "Improves testability and reduces risk of breaking query parsing.",
    },
    {
      id: "REC-03",
      type: "secure_storage",
      title: "Replace Pickle with JSON Serialization",
      severity: "high",
      target: "backend/cache/redis_store.py",
      file: "backend/cache/redis_store.py",
      rationale: "Eliminate arbitrary code execution risk during cache retrieval.",
      suggestion: "Use pydantic / json serialization for cached items.",
      effort: "Small (1 hr)",
      details: "Fixes Bandit security rule warning #S301.",
    },
  ],
};

const getMockQuery = (q: string): QueryResult => ({
  question: q || "How does the codebase ingestion pipeline work?",
  strategy: "hybrid_rag_graph",
  answer: `The **Codebase Intelligence Platform** analyzes codebases via a multi-tier pipeline:

1. **AST Extraction**: Parses Python, TypeScript, and JavaScript into Abstract Syntax Trees to extract functions, imports, and classes.
2. **Knowledge Graph**: Constructs an architectural graph in **ArcadeDB / NetworkX** tracking file dependencies (\`DEPENDS_ON\`), call flows (\`CALLS\`), and inheritance (\`EXTENDS\`).
3. **Semantic Embeddings**: Computes vector embeddings stored in **ChromaDB** for natural language code search.
4. **Risk & Impact Analysis**: Evaluates graph metrics (circularity, fan-out, complexity) to identify code smells and calculate modification blast radius.`,
  sources: [
    "backend/services/ingest.py",
    "backend/graph/builder.py",
    "backend/api/routes_query.py",
    "frontend/app/page.tsx",
  ],
  cypher: "MATCH (f:File)-[r:DEPENDS_ON]->(target:File) RETURN f.path, target.path LIMIT 25",
});

const getMockImpact = (filePath: string): ImpactResult => ({
  target: filePath || "backend/database/models.py",
  directly_affected_count: 3,
  transitively_affected_count: 5,
  risk_level: "High",
  directly_affected: [
    { name: "backend/auth/service.py", file: "backend/auth/service.py", hops: 1 },
    { name: "backend/api/routes_user.py", file: "backend/api/routes_user.py", hops: 1 },
    { name: "backend/database/session.py", file: "backend/database/session.py", hops: 1 },
  ],
  transitively_affected: [
    { name: "backend/main.py", file: "backend/main.py", hops: 2 },
    { name: "backend/services/celery_worker.py", file: "backend/services/celery_worker.py", hops: 2 },
    { name: "backend/tests/test_auth.py", file: "backend/tests/test_auth.py", hops: 2 },
    { name: "backend/api/admin_routes.py", file: "backend/api/admin_routes.py", hops: 3 },
    { name: "frontend/lib/api.ts", file: "frontend/lib/api.ts", hops: 3 },
  ],
});

const MOCK_HOTSPOTS: HotspotResult = {
  available: true,
  mode: "churn_x_complexity",
  repo_path: "codebase_intelligence_project",
  total: 4,
  hotspots: [
    {
      file: "backend/database/models.py",
      churn: 42,
      total_complexity: 128,
      max_complexity: 24,
      functions: 14,
      lines_of_code: 450,
      score: 98,
    },
    {
      file: "backend/api/routes_query.py",
      churn: 38,
      total_complexity: 145,
      max_complexity: 32,
      functions: 18,
      lines_of_code: 620,
      score: 92,
    },
    {
      file: "backend/services/ingest.py",
      churn: 29,
      total_complexity: 95,
      max_complexity: 18,
      functions: 12,
      lines_of_code: 380,
      score: 84,
    },
    {
      file: "backend/graph/builder.py",
      churn: 21,
      total_complexity: 88,
      max_complexity: 16,
      functions: 10,
      lines_of_code: 310,
      score: 76,
    },
  ],
};

const MOCK_REPO_FILES: RepoFiles = {
  repo_path: "goyal-harshit/codebase-intelligence-platform",
  count: 8,
  files: [
    "backend/database/models.py",
    "backend/api/routes_query.py",
    "backend/services/ingest.py",
    "backend/graph/builder.py",
    "backend/cache/redis_store.py",
    "frontend/app/page.tsx",
    "frontend/components/Nav.tsx",
    "backend/config/settings.py",
  ],
};

const MOCK_SERVICE_HEALTH: ServiceHealth = {
  all_ok: true,
  services: {
    postgres: { ok: true, url: "postgresql+psycopg2://postgres@localhost:5432/codebase" },
    redis: { ok: true, url: "redis://localhost:6379/0" },
    arcadedb: { ok: true, url: "http://localhost:2480" },
    chromadb: { ok: true, url: "http://localhost:8000" },
    llm: { ok: true, url: "http://localhost:11434/v1", model: "qwen2.5-coder:7b", model_present: true },
  },
};

const MOCK_LLM_CONFIG: LlmConfig = {
  provider: "ollama",
  base_url: "http://localhost:11434/v1",
  model: "qwen2.5-coder:7b",
  api_key_set: true,
  source: "env",
};

const MOCK_LLM_MODELS: LlmModels = {
  provider: "ollama",
  available: true,
  models: ["qwen2.5-coder:7b", "llama3:8b", "codellama:13b"],
};

const MOCK_INGEST_JOB: IngestJob = {
  job_id: "demo-job-001",
  status: "completed",
  step: "Done",
  progress: 100,
  repo_url: "https://github.com/goyal-harshit/codebase-intelligence-platform",
  warnings: [],
};

const MOCK_GRAPHIFY_STATS: GraphifyStats = {
  nodes: 320,
  edges: 1000,
  communities: 8,
  available: true,
};

const MOCK_GRAPHIFY_GRAPH: GraphifyGraph = {
  community_labels: {
    "0": "Core API & Routing",
    "1": "Database & ORM Layer",
    "2": "AST Ingestion Engine",
    "3": "Graph Topology & Analysis",
    "4": "Vector Search & RAG Pipeline",
    "5": "Frontend Web Application",
    "6": "Security & Compliance Scanners",
    "7": "Standalone Utilities & Microservices"
},
  nodes: [
    {
        "id": "backend/api/route_01.py",
        "name": "route_01.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_01.py"
    },
    {
        "id": "backend/api/route_02.py",
        "name": "route_02.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_02.py"
    },
    {
        "id": "backend/api/route_03.py",
        "name": "route_03.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_03.py"
    },
    {
        "id": "backend/api/route_04.py",
        "name": "route_04.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_04.py"
    },
    {
        "id": "backend/api/route_05.py",
        "name": "route_05.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_05.py"
    },
    {
        "id": "backend/api/route_06.py",
        "name": "route_06.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_06.py"
    },
    {
        "id": "backend/api/route_07.py",
        "name": "route_07.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_07.py"
    },
    {
        "id": "backend/api/route_08.py",
        "name": "route_08.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_08.py"
    },
    {
        "id": "backend/api/route_09.py",
        "name": "route_09.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_09.py"
    },
    {
        "id": "backend/api/route_10.py",
        "name": "route_10.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_10.py"
    },
    {
        "id": "backend/api/route_11.py",
        "name": "route_11.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_11.py"
    },
    {
        "id": "backend/api/route_12.py",
        "name": "route_12.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_12.py"
    },
    {
        "id": "backend/api/route_13.py",
        "name": "route_13.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_13.py"
    },
    {
        "id": "backend/api/route_14.py",
        "name": "route_14.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_14.py"
    },
    {
        "id": "backend/api/route_15.py",
        "name": "route_15.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_15.py"
    },
    {
        "id": "backend/api/route_16.py",
        "name": "route_16.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_16.py"
    },
    {
        "id": "backend/api/route_17.py",
        "name": "route_17.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_17.py"
    },
    {
        "id": "backend/api/route_18.py",
        "name": "route_18.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_18.py"
    },
    {
        "id": "backend/api/route_19.py",
        "name": "route_19.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_19.py"
    },
    {
        "id": "backend/api/route_20.py",
        "name": "route_20.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_20.py"
    },
    {
        "id": "backend/api/route_21.py",
        "name": "route_21.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_21.py"
    },
    {
        "id": "backend/api/route_22.py",
        "name": "route_22.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_22.py"
    },
    {
        "id": "backend/api/route_23.py",
        "name": "route_23.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_23.py"
    },
    {
        "id": "backend/api/route_24.py",
        "name": "route_24.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_24.py"
    },
    {
        "id": "backend/api/route_25.py",
        "name": "route_25.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_25.py"
    },
    {
        "id": "backend/api/route_26.py",
        "name": "route_26.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_26.py"
    },
    {
        "id": "backend/api/route_27.py",
        "name": "route_27.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_27.py"
    },
    {
        "id": "backend/api/route_28.py",
        "name": "route_28.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_28.py"
    },
    {
        "id": "backend/api/route_29.py",
        "name": "route_29.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_29.py"
    },
    {
        "id": "backend/api/route_30.py",
        "name": "route_30.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_30.py"
    },
    {
        "id": "backend/api/route_31.py",
        "name": "route_31.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_31.py"
    },
    {
        "id": "backend/api/route_32.py",
        "name": "route_32.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_32.py"
    },
    {
        "id": "backend/api/route_33.py",
        "name": "route_33.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_33.py"
    },
    {
        "id": "backend/api/route_34.py",
        "name": "route_34.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_34.py"
    },
    {
        "id": "backend/api/route_35.py",
        "name": "route_35.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_35.py"
    },
    {
        "id": "backend/api/route_36.py",
        "name": "route_36.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_36.py"
    },
    {
        "id": "backend/api/route_37.py",
        "name": "route_37.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_37.py"
    },
    {
        "id": "backend/api/route_38.py",
        "name": "route_38.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_38.py"
    },
    {
        "id": "backend/api/route_39.py",
        "name": "route_39.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_39.py"
    },
    {
        "id": "backend/api/route_40.py",
        "name": "route_40.py",
        "type": "file",
        "community": 0,
        "file": "backend/api/route_40.py"
    },
    {
        "id": "backend/database/model_01.py",
        "name": "model_01.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_01.py"
    },
    {
        "id": "backend/database/model_02.py",
        "name": "model_02.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_02.py"
    },
    {
        "id": "backend/database/model_03.py",
        "name": "model_03.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_03.py"
    },
    {
        "id": "backend/database/model_04.py",
        "name": "model_04.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_04.py"
    },
    {
        "id": "backend/database/model_05.py",
        "name": "model_05.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_05.py"
    },
    {
        "id": "backend/database/model_06.py",
        "name": "model_06.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_06.py"
    },
    {
        "id": "backend/database/model_07.py",
        "name": "model_07.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_07.py"
    },
    {
        "id": "backend/database/model_08.py",
        "name": "model_08.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_08.py"
    },
    {
        "id": "backend/database/model_09.py",
        "name": "model_09.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_09.py"
    },
    {
        "id": "backend/database/model_10.py",
        "name": "model_10.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_10.py"
    },
    {
        "id": "backend/database/model_11.py",
        "name": "model_11.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_11.py"
    },
    {
        "id": "backend/database/model_12.py",
        "name": "model_12.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_12.py"
    },
    {
        "id": "backend/database/model_13.py",
        "name": "model_13.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_13.py"
    },
    {
        "id": "backend/database/model_14.py",
        "name": "model_14.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_14.py"
    },
    {
        "id": "backend/database/model_15.py",
        "name": "model_15.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_15.py"
    },
    {
        "id": "backend/database/model_16.py",
        "name": "model_16.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_16.py"
    },
    {
        "id": "backend/database/model_17.py",
        "name": "model_17.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_17.py"
    },
    {
        "id": "backend/database/model_18.py",
        "name": "model_18.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_18.py"
    },
    {
        "id": "backend/database/model_19.py",
        "name": "model_19.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_19.py"
    },
    {
        "id": "backend/database/model_20.py",
        "name": "model_20.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_20.py"
    },
    {
        "id": "backend/database/model_21.py",
        "name": "model_21.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_21.py"
    },
    {
        "id": "backend/database/model_22.py",
        "name": "model_22.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_22.py"
    },
    {
        "id": "backend/database/model_23.py",
        "name": "model_23.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_23.py"
    },
    {
        "id": "backend/database/model_24.py",
        "name": "model_24.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_24.py"
    },
    {
        "id": "backend/database/model_25.py",
        "name": "model_25.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_25.py"
    },
    {
        "id": "backend/database/model_26.py",
        "name": "model_26.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_26.py"
    },
    {
        "id": "backend/database/model_27.py",
        "name": "model_27.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_27.py"
    },
    {
        "id": "backend/database/model_28.py",
        "name": "model_28.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_28.py"
    },
    {
        "id": "backend/database/model_29.py",
        "name": "model_29.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_29.py"
    },
    {
        "id": "backend/database/model_30.py",
        "name": "model_30.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_30.py"
    },
    {
        "id": "backend/database/model_31.py",
        "name": "model_31.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_31.py"
    },
    {
        "id": "backend/database/model_32.py",
        "name": "model_32.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_32.py"
    },
    {
        "id": "backend/database/model_33.py",
        "name": "model_33.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_33.py"
    },
    {
        "id": "backend/database/model_34.py",
        "name": "model_34.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_34.py"
    },
    {
        "id": "backend/database/model_35.py",
        "name": "model_35.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_35.py"
    },
    {
        "id": "backend/database/model_36.py",
        "name": "model_36.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_36.py"
    },
    {
        "id": "backend/database/model_37.py",
        "name": "model_37.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_37.py"
    },
    {
        "id": "backend/database/model_38.py",
        "name": "model_38.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_38.py"
    },
    {
        "id": "backend/database/model_39.py",
        "name": "model_39.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_39.py"
    },
    {
        "id": "backend/database/model_40.py",
        "name": "model_40.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_40.py"
    },
    {
        "id": "backend/database/model_41.py",
        "name": "model_41.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_41.py"
    },
    {
        "id": "backend/database/model_42.py",
        "name": "model_42.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_42.py"
    },
    {
        "id": "backend/database/model_43.py",
        "name": "model_43.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_43.py"
    },
    {
        "id": "backend/database/model_44.py",
        "name": "model_44.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_44.py"
    },
    {
        "id": "backend/database/model_45.py",
        "name": "model_45.py",
        "type": "file",
        "community": 1,
        "file": "backend/database/model_45.py"
    },
    {
        "id": "backend/parser/ast_parser_01.py",
        "name": "ast_parser_01.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_01.py"
    },
    {
        "id": "backend/parser/ast_parser_02.py",
        "name": "ast_parser_02.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_02.py"
    },
    {
        "id": "backend/parser/ast_parser_03.py",
        "name": "ast_parser_03.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_03.py"
    },
    {
        "id": "backend/parser/ast_parser_04.py",
        "name": "ast_parser_04.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_04.py"
    },
    {
        "id": "backend/parser/ast_parser_05.py",
        "name": "ast_parser_05.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_05.py"
    },
    {
        "id": "backend/parser/ast_parser_06.py",
        "name": "ast_parser_06.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_06.py"
    },
    {
        "id": "backend/parser/ast_parser_07.py",
        "name": "ast_parser_07.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_07.py"
    },
    {
        "id": "backend/parser/ast_parser_08.py",
        "name": "ast_parser_08.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_08.py"
    },
    {
        "id": "backend/parser/ast_parser_09.py",
        "name": "ast_parser_09.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_09.py"
    },
    {
        "id": "backend/parser/ast_parser_10.py",
        "name": "ast_parser_10.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_10.py"
    },
    {
        "id": "backend/parser/ast_parser_11.py",
        "name": "ast_parser_11.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_11.py"
    },
    {
        "id": "backend/parser/ast_parser_12.py",
        "name": "ast_parser_12.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_12.py"
    },
    {
        "id": "backend/parser/ast_parser_13.py",
        "name": "ast_parser_13.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_13.py"
    },
    {
        "id": "backend/parser/ast_parser_14.py",
        "name": "ast_parser_14.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_14.py"
    },
    {
        "id": "backend/parser/ast_parser_15.py",
        "name": "ast_parser_15.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_15.py"
    },
    {
        "id": "backend/parser/ast_parser_16.py",
        "name": "ast_parser_16.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_16.py"
    },
    {
        "id": "backend/parser/ast_parser_17.py",
        "name": "ast_parser_17.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_17.py"
    },
    {
        "id": "backend/parser/ast_parser_18.py",
        "name": "ast_parser_18.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_18.py"
    },
    {
        "id": "backend/parser/ast_parser_19.py",
        "name": "ast_parser_19.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_19.py"
    },
    {
        "id": "backend/parser/ast_parser_20.py",
        "name": "ast_parser_20.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_20.py"
    },
    {
        "id": "backend/parser/ast_parser_21.py",
        "name": "ast_parser_21.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_21.py"
    },
    {
        "id": "backend/parser/ast_parser_22.py",
        "name": "ast_parser_22.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_22.py"
    },
    {
        "id": "backend/parser/ast_parser_23.py",
        "name": "ast_parser_23.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_23.py"
    },
    {
        "id": "backend/parser/ast_parser_24.py",
        "name": "ast_parser_24.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_24.py"
    },
    {
        "id": "backend/parser/ast_parser_25.py",
        "name": "ast_parser_25.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_25.py"
    },
    {
        "id": "backend/parser/ast_parser_26.py",
        "name": "ast_parser_26.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_26.py"
    },
    {
        "id": "backend/parser/ast_parser_27.py",
        "name": "ast_parser_27.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_27.py"
    },
    {
        "id": "backend/parser/ast_parser_28.py",
        "name": "ast_parser_28.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_28.py"
    },
    {
        "id": "backend/parser/ast_parser_29.py",
        "name": "ast_parser_29.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_29.py"
    },
    {
        "id": "backend/parser/ast_parser_30.py",
        "name": "ast_parser_30.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_30.py"
    },
    {
        "id": "backend/parser/ast_parser_31.py",
        "name": "ast_parser_31.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_31.py"
    },
    {
        "id": "backend/parser/ast_parser_32.py",
        "name": "ast_parser_32.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_32.py"
    },
    {
        "id": "backend/parser/ast_parser_33.py",
        "name": "ast_parser_33.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_33.py"
    },
    {
        "id": "backend/parser/ast_parser_34.py",
        "name": "ast_parser_34.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_34.py"
    },
    {
        "id": "backend/parser/ast_parser_35.py",
        "name": "ast_parser_35.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_35.py"
    },
    {
        "id": "backend/parser/ast_parser_36.py",
        "name": "ast_parser_36.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_36.py"
    },
    {
        "id": "backend/parser/ast_parser_37.py",
        "name": "ast_parser_37.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_37.py"
    },
    {
        "id": "backend/parser/ast_parser_38.py",
        "name": "ast_parser_38.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_38.py"
    },
    {
        "id": "backend/parser/ast_parser_39.py",
        "name": "ast_parser_39.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_39.py"
    },
    {
        "id": "backend/parser/ast_parser_40.py",
        "name": "ast_parser_40.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_40.py"
    },
    {
        "id": "backend/parser/ast_parser_41.py",
        "name": "ast_parser_41.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_41.py"
    },
    {
        "id": "backend/parser/ast_parser_42.py",
        "name": "ast_parser_42.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_42.py"
    },
    {
        "id": "backend/parser/ast_parser_43.py",
        "name": "ast_parser_43.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_43.py"
    },
    {
        "id": "backend/parser/ast_parser_44.py",
        "name": "ast_parser_44.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_44.py"
    },
    {
        "id": "backend/parser/ast_parser_45.py",
        "name": "ast_parser_45.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_45.py"
    },
    {
        "id": "backend/parser/ast_parser_46.py",
        "name": "ast_parser_46.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_46.py"
    },
    {
        "id": "backend/parser/ast_parser_47.py",
        "name": "ast_parser_47.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_47.py"
    },
    {
        "id": "backend/parser/ast_parser_48.py",
        "name": "ast_parser_48.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_48.py"
    },
    {
        "id": "backend/parser/ast_parser_49.py",
        "name": "ast_parser_49.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_49.py"
    },
    {
        "id": "backend/parser/ast_parser_50.py",
        "name": "ast_parser_50.py",
        "type": "file",
        "community": 2,
        "file": "backend/parser/ast_parser_50.py"
    },
    {
        "id": "backend/graph/graph_engine_01.py",
        "name": "graph_engine_01.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_01.py"
    },
    {
        "id": "backend/graph/graph_engine_02.py",
        "name": "graph_engine_02.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_02.py"
    },
    {
        "id": "backend/graph/graph_engine_03.py",
        "name": "graph_engine_03.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_03.py"
    },
    {
        "id": "backend/graph/graph_engine_04.py",
        "name": "graph_engine_04.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_04.py"
    },
    {
        "id": "backend/graph/graph_engine_05.py",
        "name": "graph_engine_05.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_05.py"
    },
    {
        "id": "backend/graph/graph_engine_06.py",
        "name": "graph_engine_06.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_06.py"
    },
    {
        "id": "backend/graph/graph_engine_07.py",
        "name": "graph_engine_07.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_07.py"
    },
    {
        "id": "backend/graph/graph_engine_08.py",
        "name": "graph_engine_08.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_08.py"
    },
    {
        "id": "backend/graph/graph_engine_09.py",
        "name": "graph_engine_09.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_09.py"
    },
    {
        "id": "backend/graph/graph_engine_10.py",
        "name": "graph_engine_10.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_10.py"
    },
    {
        "id": "backend/graph/graph_engine_11.py",
        "name": "graph_engine_11.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_11.py"
    },
    {
        "id": "backend/graph/graph_engine_12.py",
        "name": "graph_engine_12.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_12.py"
    },
    {
        "id": "backend/graph/graph_engine_13.py",
        "name": "graph_engine_13.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_13.py"
    },
    {
        "id": "backend/graph/graph_engine_14.py",
        "name": "graph_engine_14.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_14.py"
    },
    {
        "id": "backend/graph/graph_engine_15.py",
        "name": "graph_engine_15.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_15.py"
    },
    {
        "id": "backend/graph/graph_engine_16.py",
        "name": "graph_engine_16.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_16.py"
    },
    {
        "id": "backend/graph/graph_engine_17.py",
        "name": "graph_engine_17.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_17.py"
    },
    {
        "id": "backend/graph/graph_engine_18.py",
        "name": "graph_engine_18.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_18.py"
    },
    {
        "id": "backend/graph/graph_engine_19.py",
        "name": "graph_engine_19.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_19.py"
    },
    {
        "id": "backend/graph/graph_engine_20.py",
        "name": "graph_engine_20.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_20.py"
    },
    {
        "id": "backend/graph/graph_engine_21.py",
        "name": "graph_engine_21.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_21.py"
    },
    {
        "id": "backend/graph/graph_engine_22.py",
        "name": "graph_engine_22.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_22.py"
    },
    {
        "id": "backend/graph/graph_engine_23.py",
        "name": "graph_engine_23.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_23.py"
    },
    {
        "id": "backend/graph/graph_engine_24.py",
        "name": "graph_engine_24.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_24.py"
    },
    {
        "id": "backend/graph/graph_engine_25.py",
        "name": "graph_engine_25.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_25.py"
    },
    {
        "id": "backend/graph/graph_engine_26.py",
        "name": "graph_engine_26.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_26.py"
    },
    {
        "id": "backend/graph/graph_engine_27.py",
        "name": "graph_engine_27.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_27.py"
    },
    {
        "id": "backend/graph/graph_engine_28.py",
        "name": "graph_engine_28.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_28.py"
    },
    {
        "id": "backend/graph/graph_engine_29.py",
        "name": "graph_engine_29.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_29.py"
    },
    {
        "id": "backend/graph/graph_engine_30.py",
        "name": "graph_engine_30.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_30.py"
    },
    {
        "id": "backend/graph/graph_engine_31.py",
        "name": "graph_engine_31.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_31.py"
    },
    {
        "id": "backend/graph/graph_engine_32.py",
        "name": "graph_engine_32.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_32.py"
    },
    {
        "id": "backend/graph/graph_engine_33.py",
        "name": "graph_engine_33.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_33.py"
    },
    {
        "id": "backend/graph/graph_engine_34.py",
        "name": "graph_engine_34.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_34.py"
    },
    {
        "id": "backend/graph/graph_engine_35.py",
        "name": "graph_engine_35.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_35.py"
    },
    {
        "id": "backend/graph/graph_engine_36.py",
        "name": "graph_engine_36.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_36.py"
    },
    {
        "id": "backend/graph/graph_engine_37.py",
        "name": "graph_engine_37.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_37.py"
    },
    {
        "id": "backend/graph/graph_engine_38.py",
        "name": "graph_engine_38.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_38.py"
    },
    {
        "id": "backend/graph/graph_engine_39.py",
        "name": "graph_engine_39.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_39.py"
    },
    {
        "id": "backend/graph/graph_engine_40.py",
        "name": "graph_engine_40.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_40.py"
    },
    {
        "id": "backend/graph/graph_engine_41.py",
        "name": "graph_engine_41.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_41.py"
    },
    {
        "id": "backend/graph/graph_engine_42.py",
        "name": "graph_engine_42.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_42.py"
    },
    {
        "id": "backend/graph/graph_engine_43.py",
        "name": "graph_engine_43.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_43.py"
    },
    {
        "id": "backend/graph/graph_engine_44.py",
        "name": "graph_engine_44.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_44.py"
    },
    {
        "id": "backend/graph/graph_engine_45.py",
        "name": "graph_engine_45.py",
        "type": "file",
        "community": 3,
        "file": "backend/graph/graph_engine_45.py"
    },
    {
        "id": "backend/rag/vector_service_01.py",
        "name": "vector_service_01.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_01.py"
    },
    {
        "id": "backend/rag/vector_service_02.py",
        "name": "vector_service_02.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_02.py"
    },
    {
        "id": "backend/rag/vector_service_03.py",
        "name": "vector_service_03.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_03.py"
    },
    {
        "id": "backend/rag/vector_service_04.py",
        "name": "vector_service_04.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_04.py"
    },
    {
        "id": "backend/rag/vector_service_05.py",
        "name": "vector_service_05.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_05.py"
    },
    {
        "id": "backend/rag/vector_service_06.py",
        "name": "vector_service_06.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_06.py"
    },
    {
        "id": "backend/rag/vector_service_07.py",
        "name": "vector_service_07.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_07.py"
    },
    {
        "id": "backend/rag/vector_service_08.py",
        "name": "vector_service_08.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_08.py"
    },
    {
        "id": "backend/rag/vector_service_09.py",
        "name": "vector_service_09.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_09.py"
    },
    {
        "id": "backend/rag/vector_service_10.py",
        "name": "vector_service_10.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_10.py"
    },
    {
        "id": "backend/rag/vector_service_11.py",
        "name": "vector_service_11.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_11.py"
    },
    {
        "id": "backend/rag/vector_service_12.py",
        "name": "vector_service_12.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_12.py"
    },
    {
        "id": "backend/rag/vector_service_13.py",
        "name": "vector_service_13.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_13.py"
    },
    {
        "id": "backend/rag/vector_service_14.py",
        "name": "vector_service_14.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_14.py"
    },
    {
        "id": "backend/rag/vector_service_15.py",
        "name": "vector_service_15.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_15.py"
    },
    {
        "id": "backend/rag/vector_service_16.py",
        "name": "vector_service_16.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_16.py"
    },
    {
        "id": "backend/rag/vector_service_17.py",
        "name": "vector_service_17.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_17.py"
    },
    {
        "id": "backend/rag/vector_service_18.py",
        "name": "vector_service_18.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_18.py"
    },
    {
        "id": "backend/rag/vector_service_19.py",
        "name": "vector_service_19.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_19.py"
    },
    {
        "id": "backend/rag/vector_service_20.py",
        "name": "vector_service_20.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_20.py"
    },
    {
        "id": "backend/rag/vector_service_21.py",
        "name": "vector_service_21.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_21.py"
    },
    {
        "id": "backend/rag/vector_service_22.py",
        "name": "vector_service_22.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_22.py"
    },
    {
        "id": "backend/rag/vector_service_23.py",
        "name": "vector_service_23.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_23.py"
    },
    {
        "id": "backend/rag/vector_service_24.py",
        "name": "vector_service_24.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_24.py"
    },
    {
        "id": "backend/rag/vector_service_25.py",
        "name": "vector_service_25.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_25.py"
    },
    {
        "id": "backend/rag/vector_service_26.py",
        "name": "vector_service_26.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_26.py"
    },
    {
        "id": "backend/rag/vector_service_27.py",
        "name": "vector_service_27.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_27.py"
    },
    {
        "id": "backend/rag/vector_service_28.py",
        "name": "vector_service_28.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_28.py"
    },
    {
        "id": "backend/rag/vector_service_29.py",
        "name": "vector_service_29.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_29.py"
    },
    {
        "id": "backend/rag/vector_service_30.py",
        "name": "vector_service_30.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_30.py"
    },
    {
        "id": "backend/rag/vector_service_31.py",
        "name": "vector_service_31.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_31.py"
    },
    {
        "id": "backend/rag/vector_service_32.py",
        "name": "vector_service_32.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_32.py"
    },
    {
        "id": "backend/rag/vector_service_33.py",
        "name": "vector_service_33.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_33.py"
    },
    {
        "id": "backend/rag/vector_service_34.py",
        "name": "vector_service_34.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_34.py"
    },
    {
        "id": "backend/rag/vector_service_35.py",
        "name": "vector_service_35.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_35.py"
    },
    {
        "id": "backend/rag/vector_service_36.py",
        "name": "vector_service_36.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_36.py"
    },
    {
        "id": "backend/rag/vector_service_37.py",
        "name": "vector_service_37.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_37.py"
    },
    {
        "id": "backend/rag/vector_service_38.py",
        "name": "vector_service_38.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_38.py"
    },
    {
        "id": "backend/rag/vector_service_39.py",
        "name": "vector_service_39.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_39.py"
    },
    {
        "id": "backend/rag/vector_service_40.py",
        "name": "vector_service_40.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_40.py"
    },
    {
        "id": "backend/rag/vector_service_41.py",
        "name": "vector_service_41.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_41.py"
    },
    {
        "id": "backend/rag/vector_service_42.py",
        "name": "vector_service_42.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_42.py"
    },
    {
        "id": "backend/rag/vector_service_43.py",
        "name": "vector_service_43.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_43.py"
    },
    {
        "id": "backend/rag/vector_service_44.py",
        "name": "vector_service_44.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_44.py"
    },
    {
        "id": "backend/rag/vector_service_45.py",
        "name": "vector_service_45.py",
        "type": "file",
        "community": 4,
        "file": "backend/rag/vector_service_45.py"
    },
    {
        "id": "frontend/components/ui/component_01.tsx",
        "name": "component_01.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_01.tsx"
    },
    {
        "id": "frontend/components/ui/component_02.tsx",
        "name": "component_02.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_02.tsx"
    },
    {
        "id": "frontend/components/ui/component_03.tsx",
        "name": "component_03.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_03.tsx"
    },
    {
        "id": "frontend/components/ui/component_04.tsx",
        "name": "component_04.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_04.tsx"
    },
    {
        "id": "frontend/components/ui/component_05.tsx",
        "name": "component_05.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_05.tsx"
    },
    {
        "id": "frontend/components/ui/component_06.tsx",
        "name": "component_06.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_06.tsx"
    },
    {
        "id": "frontend/components/ui/component_07.tsx",
        "name": "component_07.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_07.tsx"
    },
    {
        "id": "frontend/components/ui/component_08.tsx",
        "name": "component_08.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_08.tsx"
    },
    {
        "id": "frontend/components/ui/component_09.tsx",
        "name": "component_09.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_09.tsx"
    },
    {
        "id": "frontend/components/ui/component_10.tsx",
        "name": "component_10.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_10.tsx"
    },
    {
        "id": "frontend/components/ui/component_11.tsx",
        "name": "component_11.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_11.tsx"
    },
    {
        "id": "frontend/components/ui/component_12.tsx",
        "name": "component_12.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_12.tsx"
    },
    {
        "id": "frontend/components/ui/component_13.tsx",
        "name": "component_13.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_13.tsx"
    },
    {
        "id": "frontend/components/ui/component_14.tsx",
        "name": "component_14.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_14.tsx"
    },
    {
        "id": "frontend/components/ui/component_15.tsx",
        "name": "component_15.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_15.tsx"
    },
    {
        "id": "frontend/components/ui/component_16.tsx",
        "name": "component_16.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_16.tsx"
    },
    {
        "id": "frontend/components/ui/component_17.tsx",
        "name": "component_17.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_17.tsx"
    },
    {
        "id": "frontend/components/ui/component_18.tsx",
        "name": "component_18.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_18.tsx"
    },
    {
        "id": "frontend/components/ui/component_19.tsx",
        "name": "component_19.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_19.tsx"
    },
    {
        "id": "frontend/components/ui/component_20.tsx",
        "name": "component_20.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_20.tsx"
    },
    {
        "id": "frontend/components/ui/component_21.tsx",
        "name": "component_21.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_21.tsx"
    },
    {
        "id": "frontend/components/ui/component_22.tsx",
        "name": "component_22.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_22.tsx"
    },
    {
        "id": "frontend/components/ui/component_23.tsx",
        "name": "component_23.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_23.tsx"
    },
    {
        "id": "frontend/components/ui/component_24.tsx",
        "name": "component_24.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_24.tsx"
    },
    {
        "id": "frontend/components/ui/component_25.tsx",
        "name": "component_25.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_25.tsx"
    },
    {
        "id": "frontend/components/ui/component_26.tsx",
        "name": "component_26.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_26.tsx"
    },
    {
        "id": "frontend/components/ui/component_27.tsx",
        "name": "component_27.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_27.tsx"
    },
    {
        "id": "frontend/components/ui/component_28.tsx",
        "name": "component_28.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_28.tsx"
    },
    {
        "id": "frontend/components/ui/component_29.tsx",
        "name": "component_29.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_29.tsx"
    },
    {
        "id": "frontend/components/ui/component_30.tsx",
        "name": "component_30.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_30.tsx"
    },
    {
        "id": "frontend/components/ui/component_31.tsx",
        "name": "component_31.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_31.tsx"
    },
    {
        "id": "frontend/components/ui/component_32.tsx",
        "name": "component_32.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_32.tsx"
    },
    {
        "id": "frontend/components/ui/component_33.tsx",
        "name": "component_33.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_33.tsx"
    },
    {
        "id": "frontend/components/ui/component_34.tsx",
        "name": "component_34.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_34.tsx"
    },
    {
        "id": "frontend/components/ui/component_35.tsx",
        "name": "component_35.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_35.tsx"
    },
    {
        "id": "frontend/components/ui/component_36.tsx",
        "name": "component_36.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_36.tsx"
    },
    {
        "id": "frontend/components/ui/component_37.tsx",
        "name": "component_37.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_37.tsx"
    },
    {
        "id": "frontend/components/ui/component_38.tsx",
        "name": "component_38.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_38.tsx"
    },
    {
        "id": "frontend/components/ui/component_39.tsx",
        "name": "component_39.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_39.tsx"
    },
    {
        "id": "frontend/components/ui/component_40.tsx",
        "name": "component_40.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_40.tsx"
    },
    {
        "id": "frontend/components/ui/component_41.tsx",
        "name": "component_41.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_41.tsx"
    },
    {
        "id": "frontend/components/ui/component_42.tsx",
        "name": "component_42.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_42.tsx"
    },
    {
        "id": "frontend/components/ui/component_43.tsx",
        "name": "component_43.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_43.tsx"
    },
    {
        "id": "frontend/components/ui/component_44.tsx",
        "name": "component_44.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_44.tsx"
    },
    {
        "id": "frontend/components/ui/component_45.tsx",
        "name": "component_45.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_45.tsx"
    },
    {
        "id": "frontend/components/ui/component_46.tsx",
        "name": "component_46.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_46.tsx"
    },
    {
        "id": "frontend/components/ui/component_47.tsx",
        "name": "component_47.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_47.tsx"
    },
    {
        "id": "frontend/components/ui/component_48.tsx",
        "name": "component_48.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_48.tsx"
    },
    {
        "id": "frontend/components/ui/component_49.tsx",
        "name": "component_49.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_49.tsx"
    },
    {
        "id": "frontend/components/ui/component_50.tsx",
        "name": "component_50.tsx",
        "type": "file",
        "community": 5,
        "file": "frontend/components/ui/component_50.tsx"
    },
    {
        "id": "backend/security/scanner_01.py",
        "name": "scanner_01.py",
        "type": "file",
        "community": 6,
        "file": "backend/security/scanner_01.py"
    },
    {
        "id": "backend/security/scanner_02.py",
        "name": "scanner_02.py",
        "type": "file",
        "community": 6,
        "file": "backend/security/scanner_02.py"
    },
    {
        "id": "backend/security/scanner_03.py",
        "name": "scanner_03.py",
        "type": "file",
        "community": 6,
        "file": "backend/security/scanner_03.py"
    },
    {
        "id": "backend/security/scanner_04.py",
        "name": "scanner_04.py",
        "type": "file",
        "community": 6,
        "file": "backend/security/scanner_04.py"
    },
    {
        "id": "backend/security/scanner_05.py",
        "name": "scanner_05.py",
        "type": "file",
        "community": 6,
        "file": "backend/security/scanner_05.py"
    },
    {
        "id": "backend/security/scanner_06.py",
        "name": "scanner_06.py",
        "type": "file",
        "community": 6,
        "file": "backend/security/scanner_06.py"
    },
    {
        "id": "backend/security/scanner_07.py",
        "name": "scanner_07.py",
        "type": "file",
        "community": 6,
        "file": "backend/security/scanner_07.py"
    },
    {
        "id": "backend/security/scanner_08.py",
        "name": "scanner_08.py",
        "type": "file",
        "community": 6,
        "file": "backend/security/scanner_08.py"
    },
    {
        "id": "backend/security/scanner_09.py",
        "name": "scanner_09.py",
        "type": "file",
        "community": 6,
        "file": "backend/security/scanner_09.py"
    },
    {
        "id": "backend/security/scanner_10.py",
        "name": "scanner_10.py",
        "type": "file",
        "community": 6,
        "file": "backend/security/scanner_10.py"
    },
    {
        "id": "backend/security/scanner_11.py",
        "name": "scanner_11.py",
        "type": "file",
        "community": 6,
        "file": "backend/security/scanner_11.py"
    },
    {
        "id": "backend/security/scanner_12.py",
        "name": "scanner_12.py",
        "type": "file",
        "community": 6,
        "file": "backend/security/scanner_12.py"
    },
    {
        "id": "backend/security/scanner_13.py",
        "name": "scanner_13.py",
        "type": "file",
        "community": 6,
        "file": "backend/security/scanner_13.py"
    },
    {
        "id": "backend/security/scanner_14.py",
        "name": "scanner_14.py",
        "type": "file",
        "community": 6,
        "file": "backend/security/scanner_14.py"
    },
    {
        "id": "backend/security/scanner_15.py",
        "name": "scanner_15.py",
        "type": "file",
        "community": 6,
        "file": "backend/security/scanner_15.py"
    },
    {
        "id": "backend/security/scanner_16.py",
        "name": "scanner_16.py",
        "type": "file",
        "community": 6,
        "file": "backend/security/scanner_16.py"
    },
    {
        "id": "backend/security/scanner_17.py",
        "name": "scanner_17.py",
        "type": "file",
        "community": 6,
        "file": "backend/security/scanner_17.py"
    },
    {
        "id": "backend/security/scanner_18.py",
        "name": "scanner_18.py",
        "type": "file",
        "community": 6,
        "file": "backend/security/scanner_18.py"
    },
    {
        "id": "backend/security/scanner_19.py",
        "name": "scanner_19.py",
        "type": "file",
        "community": 6,
        "file": "backend/security/scanner_19.py"
    },
    {
        "id": "backend/security/scanner_20.py",
        "name": "scanner_20.py",
        "type": "file",
        "community": 6,
        "file": "backend/security/scanner_20.py"
    },
    {
        "id": "utils/helpers/standalone_util_01.py",
        "name": "standalone_util_01.py",
        "type": "file",
        "community": 7,
        "file": "utils/helpers/standalone_util_01.py"
    },
    {
        "id": "utils/helpers/standalone_util_02.py",
        "name": "standalone_util_02.py",
        "type": "file",
        "community": 7,
        "file": "utils/helpers/standalone_util_02.py"
    },
    {
        "id": "utils/helpers/standalone_util_03.py",
        "name": "standalone_util_03.py",
        "type": "file",
        "community": 7,
        "file": "utils/helpers/standalone_util_03.py"
    },
    {
        "id": "utils/helpers/standalone_util_04.py",
        "name": "standalone_util_04.py",
        "type": "file",
        "community": 7,
        "file": "utils/helpers/standalone_util_04.py"
    },
    {
        "id": "utils/helpers/standalone_util_05.py",
        "name": "standalone_util_05.py",
        "type": "file",
        "community": 7,
        "file": "utils/helpers/standalone_util_05.py"
    },
    {
        "id": "utils/helpers/standalone_util_06.py",
        "name": "standalone_util_06.py",
        "type": "file",
        "community": 7,
        "file": "utils/helpers/standalone_util_06.py"
    },
    {
        "id": "utils/helpers/standalone_util_07.py",
        "name": "standalone_util_07.py",
        "type": "file",
        "community": 7,
        "file": "utils/helpers/standalone_util_07.py"
    },
    {
        "id": "utils/helpers/standalone_util_08.py",
        "name": "standalone_util_08.py",
        "type": "file",
        "community": 7,
        "file": "utils/helpers/standalone_util_08.py"
    },
    {
        "id": "utils/helpers/standalone_util_09.py",
        "name": "standalone_util_09.py",
        "type": "file",
        "community": 7,
        "file": "utils/helpers/standalone_util_09.py"
    },
    {
        "id": "utils/helpers/standalone_util_10.py",
        "name": "standalone_util_10.py",
        "type": "file",
        "community": 7,
        "file": "utils/helpers/standalone_util_10.py"
    },
    {
        "id": "utils/helpers/standalone_util_11.py",
        "name": "standalone_util_11.py",
        "type": "file",
        "community": 7,
        "file": "utils/helpers/standalone_util_11.py"
    },
    {
        "id": "utils/helpers/standalone_util_12.py",
        "name": "standalone_util_12.py",
        "type": "file",
        "community": 7,
        "file": "utils/helpers/standalone_util_12.py"
    },
    {
        "id": "utils/helpers/standalone_util_13.py",
        "name": "standalone_util_13.py",
        "type": "file",
        "community": 7,
        "file": "utils/helpers/standalone_util_13.py"
    },
    {
        "id": "utils/helpers/standalone_util_14.py",
        "name": "standalone_util_14.py",
        "type": "file",
        "community": 7,
        "file": "utils/helpers/standalone_util_14.py"
    },
    {
        "id": "utils/helpers/standalone_util_15.py",
        "name": "standalone_util_15.py",
        "type": "file",
        "community": 7,
        "file": "utils/helpers/standalone_util_15.py"
    },
    {
        "id": "utils/helpers/standalone_util_16.py",
        "name": "standalone_util_16.py",
        "type": "file",
        "community": 7,
        "file": "utils/helpers/standalone_util_16.py"
    },
    {
        "id": "utils/helpers/standalone_util_17.py",
        "name": "standalone_util_17.py",
        "type": "file",
        "community": 7,
        "file": "utils/helpers/standalone_util_17.py"
    },
    {
        "id": "utils/helpers/standalone_util_18.py",
        "name": "standalone_util_18.py",
        "type": "file",
        "community": 7,
        "file": "utils/helpers/standalone_util_18.py"
    },
    {
        "id": "utils/helpers/standalone_util_19.py",
        "name": "standalone_util_19.py",
        "type": "file",
        "community": 7,
        "file": "utils/helpers/standalone_util_19.py"
    },
    {
        "id": "utils/helpers/standalone_util_20.py",
        "name": "standalone_util_20.py",
        "type": "file",
        "community": 7,
        "file": "utils/helpers/standalone_util_20.py"
    },
    {
        "id": "utils/helpers/standalone_util_21.py",
        "name": "standalone_util_21.py",
        "type": "file",
        "community": 7,
        "file": "utils/helpers/standalone_util_21.py"
    },
    {
        "id": "utils/helpers/standalone_util_22.py",
        "name": "standalone_util_22.py",
        "type": "file",
        "community": 7,
        "file": "utils/helpers/standalone_util_22.py"
    },
    {
        "id": "utils/helpers/standalone_util_23.py",
        "name": "standalone_util_23.py",
        "type": "file",
        "community": 7,
        "file": "utils/helpers/standalone_util_23.py"
    },
    {
        "id": "utils/helpers/standalone_util_24.py",
        "name": "standalone_util_24.py",
        "type": "file",
        "community": 7,
        "file": "utils/helpers/standalone_util_24.py"
    },
    {
        "id": "utils/helpers/standalone_util_25.py",
        "name": "standalone_util_25.py",
        "type": "file",
        "community": 7,
        "file": "utils/helpers/standalone_util_25.py"
    }
],
  links: [
    {
        "source": "backend/security/scanner_08.py",
        "target": "backend/security/scanner_14.py"
    },
    {
        "source": "backend/api/route_33.py",
        "target": "backend/api/route_07.py"
    },
    {
        "source": "frontend/components/ui/component_22.tsx",
        "target": "frontend/components/ui/component_23.tsx"
    },
    {
        "source": "backend/rag/vector_service_16.py",
        "target": "backend/rag/vector_service_20.py"
    },
    {
        "source": "backend/api/route_33.py",
        "target": "backend/api/route_39.py"
    },
    {
        "source": "backend/graph/graph_engine_29.py",
        "target": "backend/graph/graph_engine_17.py"
    },
    {
        "source": "backend/security/scanner_13.py",
        "target": "backend/security/scanner_14.py"
    },
    {
        "source": "backend/security/scanner_14.py",
        "target": "backend/security/scanner_15.py"
    },
    {
        "source": "backend/rag/vector_service_22.py",
        "target": "backend/rag/vector_service_23.py"
    },
    {
        "source": "backend/parser/ast_parser_39.py",
        "target": "backend/parser/ast_parser_40.py"
    },
    {
        "source": "backend/database/model_30.py",
        "target": "backend/api/route_06.py"
    },
    {
        "source": "backend/api/route_05.py",
        "target": "frontend/components/ui/component_31.tsx"
    },
    {
        "source": "backend/parser/ast_parser_11.py",
        "target": "backend/parser/ast_parser_48.py"
    },
    {
        "source": "backend/database/model_14.py",
        "target": "backend/database/model_15.py"
    },
    {
        "source": "backend/graph/graph_engine_32.py",
        "target": "backend/graph/graph_engine_41.py"
    },
    {
        "source": "utils/helpers/standalone_util_01.py",
        "target": "utils/helpers/standalone_util_02.py"
    },
    {
        "source": "backend/database/model_28.py",
        "target": "backend/database/model_12.py"
    },
    {
        "source": "backend/security/scanner_02.py",
        "target": "backend/graph/graph_engine_38.py"
    },
    {
        "source": "backend/graph/graph_engine_22.py",
        "target": "backend/security/scanner_06.py"
    },
    {
        "source": "backend/rag/vector_service_18.py",
        "target": "backend/rag/vector_service_40.py"
    },
    {
        "source": "backend/graph/graph_engine_43.py",
        "target": "backend/parser/ast_parser_49.py"
    },
    {
        "source": "backend/api/route_17.py",
        "target": "backend/database/model_04.py"
    },
    {
        "source": "backend/parser/ast_parser_07.py",
        "target": "backend/parser/ast_parser_05.py"
    },
    {
        "source": "backend/parser/ast_parser_23.py",
        "target": "backend/parser/ast_parser_24.py"
    },
    {
        "source": "frontend/components/ui/component_49.tsx",
        "target": "frontend/components/ui/component_32.tsx"
    },
    {
        "source": "backend/api/route_07.py",
        "target": "backend/api/route_23.py"
    },
    {
        "source": "backend/graph/graph_engine_32.py",
        "target": "backend/graph/graph_engine_26.py"
    },
    {
        "source": "backend/graph/graph_engine_42.py",
        "target": "backend/graph/graph_engine_05.py"
    },
    {
        "source": "backend/api/route_26.py",
        "target": "backend/graph/graph_engine_28.py"
    },
    {
        "source": "backend/rag/vector_service_40.py",
        "target": "backend/rag/vector_service_41.py"
    },
    {
        "source": "backend/graph/graph_engine_17.py",
        "target": "backend/graph/graph_engine_18.py"
    },
    {
        "source": "backend/rag/vector_service_28.py",
        "target": "backend/rag/vector_service_43.py"
    },
    {
        "source": "backend/api/route_06.py",
        "target": "backend/api/route_25.py"
    },
    {
        "source": "backend/rag/vector_service_16.py",
        "target": "backend/rag/vector_service_09.py"
    },
    {
        "source": "backend/api/route_37.py",
        "target": "backend/api/route_38.py"
    },
    {
        "source": "backend/rag/vector_service_32.py",
        "target": "backend/rag/vector_service_29.py"
    },
    {
        "source": "frontend/components/ui/component_11.tsx",
        "target": "frontend/components/ui/component_22.tsx"
    },
    {
        "source": "backend/rag/vector_service_25.py",
        "target": "backend/rag/vector_service_22.py"
    },
    {
        "source": "backend/api/route_32.py",
        "target": "backend/api/route_33.py"
    },
    {
        "source": "backend/parser/ast_parser_34.py",
        "target": "backend/parser/ast_parser_35.py"
    },
    {
        "source": "frontend/components/ui/component_29.tsx",
        "target": "frontend/components/ui/component_30.tsx"
    },
    {
        "source": "frontend/components/ui/component_10.tsx",
        "target": "frontend/components/ui/component_37.tsx"
    },
    {
        "source": "backend/parser/ast_parser_23.py",
        "target": "backend/parser/ast_parser_50.py"
    },
    {
        "source": "backend/security/scanner_15.py",
        "target": "backend/security/scanner_16.py"
    },
    {
        "source": "utils/helpers/standalone_util_04.py",
        "target": "utils/helpers/standalone_util_05.py"
    },
    {
        "source": "frontend/components/ui/component_37.tsx",
        "target": "frontend/components/ui/component_03.tsx"
    },
    {
        "source": "backend/rag/vector_service_37.py",
        "target": "backend/rag/vector_service_03.py"
    },
    {
        "source": "backend/api/route_39.py",
        "target": "backend/api/route_13.py"
    },
    {
        "source": "backend/graph/graph_engine_16.py",
        "target": "backend/graph/graph_engine_10.py"
    },
    {
        "source": "backend/security/scanner_06.py",
        "target": "backend/security/scanner_07.py"
    },
    {
        "source": "backend/rag/vector_service_17.py",
        "target": "backend/rag/vector_service_18.py"
    },
    {
        "source": "backend/api/route_13.py",
        "target": "backend/api/route_35.py"
    },
    {
        "source": "backend/api/route_06.py",
        "target": "frontend/components/ui/component_18.tsx"
    },
    {
        "source": "backend/parser/ast_parser_12.py",
        "target": "backend/parser/ast_parser_48.py"
    },
    {
        "source": "backend/parser/ast_parser_29.py",
        "target": "backend/parser/ast_parser_36.py"
    },
    {
        "source": "backend/parser/ast_parser_01.py",
        "target": "backend/parser/ast_parser_02.py"
    },
    {
        "source": "backend/graph/graph_engine_14.py",
        "target": "backend/graph/graph_engine_15.py"
    },
    {
        "source": "backend/api/route_02.py",
        "target": "backend/api/route_06.py"
    },
    {
        "source": "backend/api/route_11.py",
        "target": "backend/api/route_28.py"
    },
    {
        "source": "backend/rag/vector_service_27.py",
        "target": "backend/rag/vector_service_28.py"
    },
    {
        "source": "backend/graph/graph_engine_43.py",
        "target": "backend/rag/vector_service_20.py"
    },
    {
        "source": "backend/graph/graph_engine_10.py",
        "target": "backend/graph/graph_engine_14.py"
    },
    {
        "source": "frontend/components/ui/component_42.tsx",
        "target": "frontend/components/ui/component_10.tsx"
    },
    {
        "source": "backend/rag/vector_service_38.py",
        "target": "backend/graph/graph_engine_10.py"
    },
    {
        "source": "backend/api/route_23.py",
        "target": "backend/api/route_39.py"
    },
    {
        "source": "backend/rag/vector_service_38.py",
        "target": "backend/api/route_36.py"
    },
    {
        "source": "backend/database/model_01.py",
        "target": "backend/database/model_30.py"
    },
    {
        "source": "backend/database/model_13.py",
        "target": "backend/database/model_20.py"
    },
    {
        "source": "backend/parser/ast_parser_44.py",
        "target": "backend/api/route_15.py"
    },
    {
        "source": "backend/security/scanner_20.py",
        "target": "backend/rag/vector_service_06.py"
    },
    {
        "source": "backend/database/model_04.py",
        "target": "backend/database/model_05.py"
    },
    {
        "source": "frontend/components/ui/component_05.tsx",
        "target": "frontend/components/ui/component_11.tsx"
    },
    {
        "source": "backend/graph/graph_engine_25.py",
        "target": "backend/graph/graph_engine_45.py"
    },
    {
        "source": "backend/parser/ast_parser_41.py",
        "target": "backend/parser/ast_parser_28.py"
    },
    {
        "source": "backend/parser/ast_parser_28.py",
        "target": "backend/parser/ast_parser_01.py"
    },
    {
        "source": "frontend/components/ui/component_06.tsx",
        "target": "frontend/components/ui/component_07.tsx"
    },
    {
        "source": "frontend/components/ui/component_49.tsx",
        "target": "frontend/components/ui/component_12.tsx"
    },
    {
        "source": "backend/database/model_22.py",
        "target": "backend/security/scanner_05.py"
    },
    {
        "source": "backend/graph/graph_engine_14.py",
        "target": "backend/graph/graph_engine_27.py"
    },
    {
        "source": "backend/security/scanner_11.py",
        "target": "backend/security/scanner_17.py"
    },
    {
        "source": "backend/parser/ast_parser_44.py",
        "target": "backend/parser/ast_parser_47.py"
    },
    {
        "source": "frontend/components/ui/component_44.tsx",
        "target": "frontend/components/ui/component_04.tsx"
    },
    {
        "source": "backend/rag/vector_service_45.py",
        "target": "backend/rag/vector_service_12.py"
    },
    {
        "source": "backend/rag/vector_service_08.py",
        "target": "backend/rag/vector_service_09.py"
    },
    {
        "source": "backend/api/route_28.py",
        "target": "backend/api/route_29.py"
    },
    {
        "source": "backend/parser/ast_parser_03.py",
        "target": "backend/parser/ast_parser_20.py"
    },
    {
        "source": "frontend/components/ui/component_48.tsx",
        "target": "frontend/components/ui/component_21.tsx"
    },
    {
        "source": "backend/database/model_43.py",
        "target": "backend/database/model_21.py"
    },
    {
        "source": "backend/security/scanner_16.py",
        "target": "backend/security/scanner_13.py"
    },
    {
        "source": "backend/api/route_32.py",
        "target": "backend/api/route_02.py"
    },
    {
        "source": "utils/helpers/standalone_util_16.py",
        "target": "utils/helpers/standalone_util_17.py"
    },
    {
        "source": "backend/security/scanner_05.py",
        "target": "backend/security/scanner_14.py"
    },
    {
        "source": "backend/database/model_06.py",
        "target": "backend/database/model_32.py"
    },
    {
        "source": "frontend/components/ui/component_08.tsx",
        "target": "frontend/components/ui/component_09.tsx"
    },
    {
        "source": "frontend/components/ui/component_46.tsx",
        "target": "frontend/components/ui/component_19.tsx"
    },
    {
        "source": "backend/rag/vector_service_36.py",
        "target": "backend/rag/vector_service_34.py"
    },
    {
        "source": "backend/security/scanner_12.py",
        "target": "backend/security/scanner_13.py"
    },
    {
        "source": "backend/api/route_14.py",
        "target": "backend/api/route_37.py"
    },
    {
        "source": "backend/rag/vector_service_31.py",
        "target": "backend/rag/vector_service_32.py"
    },
    {
        "source": "backend/database/model_38.py",
        "target": "backend/database/model_37.py"
    },
    {
        "source": "backend/parser/ast_parser_33.py",
        "target": "backend/rag/vector_service_18.py"
    },
    {
        "source": "frontend/components/ui/component_17.tsx",
        "target": "frontend/components/ui/component_21.tsx"
    },
    {
        "source": "backend/graph/graph_engine_21.py",
        "target": "backend/graph/graph_engine_35.py"
    },
    {
        "source": "backend/rag/vector_service_20.py",
        "target": "backend/rag/vector_service_17.py"
    },
    {
        "source": "backend/graph/graph_engine_45.py",
        "target": "backend/graph/graph_engine_02.py"
    },
    {
        "source": "backend/rag/vector_service_07.py",
        "target": "backend/rag/vector_service_08.py"
    },
    {
        "source": "backend/database/model_43.py",
        "target": "backend/database/model_32.py"
    },
    {
        "source": "backend/database/model_27.py",
        "target": "backend/rag/vector_service_37.py"
    },
    {
        "source": "backend/database/model_04.py",
        "target": "backend/database/model_38.py"
    },
    {
        "source": "backend/parser/ast_parser_43.py",
        "target": "backend/parser/ast_parser_13.py"
    },
    {
        "source": "backend/api/route_34.py",
        "target": "backend/api/route_01.py"
    },
    {
        "source": "frontend/components/ui/component_07.tsx",
        "target": "frontend/components/ui/component_08.tsx"
    },
    {
        "source": "backend/api/route_18.py",
        "target": "backend/api/route_16.py"
    },
    {
        "source": "backend/rag/vector_service_32.py",
        "target": "backend/rag/vector_service_07.py"
    },
    {
        "source": "backend/rag/vector_service_23.py",
        "target": "backend/rag/vector_service_17.py"
    },
    {
        "source": "backend/database/model_17.py",
        "target": "backend/database/model_14.py"
    },
    {
        "source": "utils/helpers/standalone_util_10.py",
        "target": "utils/helpers/standalone_util_11.py"
    },
    {
        "source": "backend/api/route_12.py",
        "target": "backend/api/route_13.py"
    },
    {
        "source": "frontend/components/ui/component_20.tsx",
        "target": "frontend/components/ui/component_45.tsx"
    },
    {
        "source": "backend/graph/graph_engine_08.py",
        "target": "backend/graph/graph_engine_09.py"
    },
    {
        "source": "backend/rag/vector_service_38.py",
        "target": "backend/rag/vector_service_45.py"
    },
    {
        "source": "backend/rag/vector_service_39.py",
        "target": "backend/rag/vector_service_40.py"
    },
    {
        "source": "backend/rag/vector_service_38.py",
        "target": "backend/rag/vector_service_18.py"
    },
    {
        "source": "backend/api/route_38.py",
        "target": "backend/api/route_39.py"
    },
    {
        "source": "backend/api/route_10.py",
        "target": "backend/api/route_24.py"
    },
    {
        "source": "backend/parser/ast_parser_02.py",
        "target": "backend/parser/ast_parser_03.py"
    },
    {
        "source": "frontend/components/ui/component_05.tsx",
        "target": "frontend/components/ui/component_06.tsx"
    },
    {
        "source": "backend/rag/vector_service_22.py",
        "target": "backend/rag/vector_service_18.py"
    },
    {
        "source": "backend/graph/graph_engine_02.py",
        "target": "backend/graph/graph_engine_03.py"
    },
    {
        "source": "backend/graph/graph_engine_04.py",
        "target": "frontend/components/ui/component_19.tsx"
    },
    {
        "source": "backend/security/scanner_16.py",
        "target": "backend/security/scanner_17.py"
    },
    {
        "source": "backend/database/model_01.py",
        "target": "backend/database/model_25.py"
    },
    {
        "source": "backend/parser/ast_parser_23.py",
        "target": "backend/security/scanner_01.py"
    },
    {
        "source": "backend/rag/vector_service_15.py",
        "target": "backend/rag/vector_service_08.py"
    },
    {
        "source": "backend/graph/graph_engine_31.py",
        "target": "backend/graph/graph_engine_02.py"
    },
    {
        "source": "backend/parser/ast_parser_09.py",
        "target": "backend/parser/ast_parser_17.py"
    },
    {
        "source": "frontend/components/ui/component_12.tsx",
        "target": "frontend/components/ui/component_36.tsx"
    },
    {
        "source": "backend/security/scanner_03.py",
        "target": "backend/security/scanner_11.py"
    },
    {
        "source": "backend/parser/ast_parser_13.py",
        "target": "backend/parser/ast_parser_24.py"
    },
    {
        "source": "backend/rag/vector_service_44.py",
        "target": "backend/rag/vector_service_45.py"
    },
    {
        "source": "frontend/components/ui/component_25.tsx",
        "target": "backend/parser/ast_parser_39.py"
    },
    {
        "source": "backend/graph/graph_engine_42.py",
        "target": "backend/graph/graph_engine_45.py"
    },
    {
        "source": "backend/graph/graph_engine_27.py",
        "target": "backend/graph/graph_engine_04.py"
    },
    {
        "source": "backend/database/model_11.py",
        "target": "backend/database/model_25.py"
    },
    {
        "source": "backend/graph/graph_engine_22.py",
        "target": "backend/graph/graph_engine_25.py"
    },
    {
        "source": "backend/security/scanner_07.py",
        "target": "backend/security/scanner_08.py"
    },
    {
        "source": "backend/database/model_29.py",
        "target": "backend/database/model_36.py"
    },
    {
        "source": "backend/graph/graph_engine_04.py",
        "target": "backend/graph/graph_engine_36.py"
    },
    {
        "source": "frontend/components/ui/component_01.tsx",
        "target": "frontend/components/ui/component_43.tsx"
    },
    {
        "source": "backend/security/scanner_04.py",
        "target": "backend/graph/graph_engine_16.py"
    },
    {
        "source": "backend/api/route_11.py",
        "target": "backend/database/model_40.py"
    },
    {
        "source": "frontend/components/ui/component_43.tsx",
        "target": "frontend/components/ui/component_26.tsx"
    },
    {
        "source": "utils/helpers/standalone_util_05.py",
        "target": "utils/helpers/standalone_util_06.py"
    },
    {
        "source": "backend/api/route_13.py",
        "target": "backend/api/route_05.py"
    },
    {
        "source": "backend/database/model_37.py",
        "target": "backend/database/model_31.py"
    },
    {
        "source": "backend/database/model_15.py",
        "target": "backend/database/model_05.py"
    },
    {
        "source": "backend/graph/graph_engine_10.py",
        "target": "backend/graph/graph_engine_11.py"
    },
    {
        "source": "frontend/components/ui/component_18.tsx",
        "target": "frontend/components/ui/component_12.tsx"
    },
    {
        "source": "backend/database/model_22.py",
        "target": "backend/database/model_07.py"
    },
    {
        "source": "backend/rag/vector_service_01.py",
        "target": "backend/rag/vector_service_37.py"
    },
    {
        "source": "backend/api/route_02.py",
        "target": "backend/api/route_03.py"
    },
    {
        "source": "frontend/components/ui/component_34.tsx",
        "target": "frontend/components/ui/component_35.tsx"
    },
    {
        "source": "backend/database/model_09.py",
        "target": "backend/database/model_43.py"
    },
    {
        "source": "backend/database/model_02.py",
        "target": "backend/database/model_03.py"
    },
    {
        "source": "backend/parser/ast_parser_23.py",
        "target": "backend/parser/ast_parser_42.py"
    },
    {
        "source": "backend/parser/ast_parser_15.py",
        "target": "backend/rag/vector_service_42.py"
    },
    {
        "source": "backend/graph/graph_engine_01.py",
        "target": "backend/graph/graph_engine_02.py"
    },
    {
        "source": "backend/database/model_01.py",
        "target": "backend/database/model_06.py"
    },
    {
        "source": "backend/rag/vector_service_19.py",
        "target": "backend/rag/vector_service_45.py"
    },
    {
        "source": "backend/security/scanner_09.py",
        "target": "backend/security/scanner_01.py"
    },
    {
        "source": "backend/database/model_09.py",
        "target": "backend/security/scanner_18.py"
    },
    {
        "source": "backend/parser/ast_parser_13.py",
        "target": "backend/parser/ast_parser_27.py"
    },
    {
        "source": "backend/parser/ast_parser_22.py",
        "target": "backend/parser/ast_parser_14.py"
    },
    {
        "source": "frontend/components/ui/component_39.tsx",
        "target": "frontend/components/ui/component_40.tsx"
    },
    {
        "source": "backend/rag/vector_service_31.py",
        "target": "backend/rag/vector_service_18.py"
    },
    {
        "source": "backend/graph/graph_engine_19.py",
        "target": "backend/graph/graph_engine_16.py"
    },
    {
        "source": "backend/api/route_25.py",
        "target": "backend/api/route_39.py"
    },
    {
        "source": "backend/api/route_19.py",
        "target": "backend/api/route_40.py"
    },
    {
        "source": "backend/parser/ast_parser_19.py",
        "target": "backend/parser/ast_parser_39.py"
    },
    {
        "source": "backend/rag/vector_service_34.py",
        "target": "backend/rag/vector_service_42.py"
    },
    {
        "source": "backend/rag/vector_service_21.py",
        "target": "backend/rag/vector_service_22.py"
    },
    {
        "source": "backend/security/scanner_03.py",
        "target": "backend/security/scanner_04.py"
    },
    {
        "source": "backend/api/route_04.py",
        "target": "backend/api/route_05.py"
    },
    {
        "source": "backend/security/scanner_05.py",
        "target": "backend/security/scanner_13.py"
    },
    {
        "source": "backend/rag/vector_service_33.py",
        "target": "backend/rag/vector_service_42.py"
    },
    {
        "source": "backend/database/model_29.py",
        "target": "backend/database/model_09.py"
    },
    {
        "source": "backend/parser/ast_parser_37.py",
        "target": "backend/parser/ast_parser_38.py"
    },
    {
        "source": "frontend/components/ui/component_11.tsx",
        "target": "backend/database/model_12.py"
    },
    {
        "source": "backend/parser/ast_parser_21.py",
        "target": "backend/parser/ast_parser_22.py"
    },
    {
        "source": "backend/api/route_25.py",
        "target": "backend/api/route_26.py"
    },
    {
        "source": "backend/database/model_01.py",
        "target": "backend/database/model_02.py"
    },
    {
        "source": "backend/parser/ast_parser_22.py",
        "target": "backend/parser/ast_parser_27.py"
    },
    {
        "source": "backend/api/route_28.py",
        "target": "backend/api/route_03.py"
    },
    {
        "source": "backend/graph/graph_engine_19.py",
        "target": "backend/graph/graph_engine_20.py"
    },
    {
        "source": "frontend/components/ui/component_19.tsx",
        "target": "frontend/components/ui/component_03.tsx"
    },
    {
        "source": "frontend/components/ui/component_14.tsx",
        "target": "frontend/components/ui/component_18.tsx"
    },
    {
        "source": "frontend/components/ui/component_19.tsx",
        "target": "frontend/components/ui/component_20.tsx"
    },
    {
        "source": "backend/security/scanner_10.py",
        "target": "backend/graph/graph_engine_44.py"
    },
    {
        "source": "backend/database/model_40.py",
        "target": "backend/database/model_37.py"
    },
    {
        "source": "backend/graph/graph_engine_15.py",
        "target": "backend/graph/graph_engine_16.py"
    },
    {
        "source": "backend/graph/graph_engine_07.py",
        "target": "backend/graph/graph_engine_08.py"
    },
    {
        "source": "backend/graph/graph_engine_27.py",
        "target": "backend/graph/graph_engine_41.py"
    },
    {
        "source": "backend/rag/vector_service_29.py",
        "target": "backend/rag/vector_service_30.py"
    },
    {
        "source": "backend/graph/graph_engine_30.py",
        "target": "backend/graph/graph_engine_21.py"
    },
    {
        "source": "frontend/components/ui/component_20.tsx",
        "target": "frontend/components/ui/component_21.tsx"
    },
    {
        "source": "backend/api/route_08.py",
        "target": "backend/api/route_09.py"
    },
    {
        "source": "frontend/components/ui/component_21.tsx",
        "target": "frontend/components/ui/component_22.tsx"
    },
    {
        "source": "backend/database/model_20.py",
        "target": "frontend/components/ui/component_02.tsx"
    },
    {
        "source": "backend/rag/vector_service_05.py",
        "target": "backend/database/model_29.py"
    },
    {
        "source": "backend/security/scanner_05.py",
        "target": "backend/api/route_01.py"
    },
    {
        "source": "backend/parser/ast_parser_48.py",
        "target": "backend/parser/ast_parser_36.py"
    },
    {
        "source": "frontend/components/ui/component_39.tsx",
        "target": "frontend/components/ui/component_17.tsx"
    },
    {
        "source": "backend/graph/graph_engine_10.py",
        "target": "backend/api/route_15.py"
    },
    {
        "source": "backend/rag/vector_service_38.py",
        "target": "frontend/components/ui/component_36.tsx"
    },
    {
        "source": "backend/rag/vector_service_09.py",
        "target": "backend/rag/vector_service_41.py"
    },
    {
        "source": "backend/security/scanner_08.py",
        "target": "backend/security/scanner_09.py"
    },
    {
        "source": "backend/database/model_16.py",
        "target": "backend/database/model_11.py"
    },
    {
        "source": "backend/api/route_35.py",
        "target": "backend/api/route_36.py"
    },
    {
        "source": "backend/database/model_37.py",
        "target": "backend/database/model_06.py"
    },
    {
        "source": "backend/api/route_02.py",
        "target": "backend/api/route_36.py"
    },
    {
        "source": "backend/security/scanner_19.py",
        "target": "backend/security/scanner_11.py"
    },
    {
        "source": "backend/graph/graph_engine_34.py",
        "target": "backend/graph/graph_engine_35.py"
    },
    {
        "source": "backend/api/route_26.py",
        "target": "backend/api/route_27.py"
    },
    {
        "source": "backend/database/model_36.py",
        "target": "backend/database/model_15.py"
    },
    {
        "source": "frontend/components/ui/component_32.tsx",
        "target": "frontend/components/ui/component_33.tsx"
    },
    {
        "source": "frontend/components/ui/component_25.tsx",
        "target": "frontend/components/ui/component_26.tsx"
    },
    {
        "source": "frontend/components/ui/component_14.tsx",
        "target": "frontend/components/ui/component_15.tsx"
    },
    {
        "source": "backend/parser/ast_parser_17.py",
        "target": "backend/parser/ast_parser_18.py"
    },
    {
        "source": "utils/helpers/standalone_util_17.py",
        "target": "utils/helpers/standalone_util_18.py"
    },
    {
        "source": "backend/api/route_14.py",
        "target": "backend/rag/vector_service_38.py"
    },
    {
        "source": "backend/graph/graph_engine_10.py",
        "target": "backend/graph/graph_engine_15.py"
    },
    {
        "source": "backend/api/route_10.py",
        "target": "backend/api/route_14.py"
    },
    {
        "source": "frontend/components/ui/component_40.tsx",
        "target": "frontend/components/ui/component_04.tsx"
    },
    {
        "source": "backend/api/route_16.py",
        "target": "backend/api/route_36.py"
    },
    {
        "source": "backend/parser/ast_parser_44.py",
        "target": "backend/parser/ast_parser_41.py"
    },
    {
        "source": "backend/database/model_37.py",
        "target": "backend/security/scanner_13.py"
    },
    {
        "source": "backend/rag/vector_service_43.py",
        "target": "backend/rag/vector_service_38.py"
    },
    {
        "source": "backend/rag/vector_service_31.py",
        "target": "backend/rag/vector_service_42.py"
    },
    {
        "source": "backend/parser/ast_parser_47.py",
        "target": "backend/parser/ast_parser_20.py"
    },
    {
        "source": "backend/parser/ast_parser_30.py",
        "target": "backend/parser/ast_parser_31.py"
    },
    {
        "source": "backend/parser/ast_parser_33.py",
        "target": "backend/parser/ast_parser_26.py"
    },
    {
        "source": "backend/graph/graph_engine_15.py",
        "target": "backend/graph/graph_engine_32.py"
    },
    {
        "source": "backend/api/route_17.py",
        "target": "backend/api/route_18.py"
    },
    {
        "source": "backend/rag/vector_service_32.py",
        "target": "backend/rag/vector_service_36.py"
    },
    {
        "source": "frontend/components/ui/component_04.tsx",
        "target": "frontend/components/ui/component_17.tsx"
    },
    {
        "source": "backend/graph/graph_engine_05.py",
        "target": "backend/graph/graph_engine_30.py"
    },
    {
        "source": "frontend/components/ui/component_13.tsx",
        "target": "frontend/components/ui/component_14.tsx"
    },
    {
        "source": "backend/graph/graph_engine_12.py",
        "target": "backend/graph/graph_engine_04.py"
    },
    {
        "source": "backend/database/model_27.py",
        "target": "backend/database/model_32.py"
    },
    {
        "source": "backend/graph/graph_engine_32.py",
        "target": "backend/graph/graph_engine_33.py"
    },
    {
        "source": "backend/database/model_10.py",
        "target": "backend/database/model_11.py"
    },
    {
        "source": "frontend/components/ui/component_27.tsx",
        "target": "frontend/components/ui/component_28.tsx"
    },
    {
        "source": "frontend/components/ui/component_13.tsx",
        "target": "frontend/components/ui/component_34.tsx"
    },
    {
        "source": "backend/parser/ast_parser_10.py",
        "target": "backend/parser/ast_parser_16.py"
    },
    {
        "source": "backend/graph/graph_engine_01.py",
        "target": "backend/graph/graph_engine_07.py"
    },
    {
        "source": "backend/parser/ast_parser_26.py",
        "target": "backend/api/route_01.py"
    },
    {
        "source": "backend/parser/ast_parser_11.py",
        "target": "backend/parser/ast_parser_45.py"
    },
    {
        "source": "backend/rag/vector_service_31.py",
        "target": "backend/rag/vector_service_43.py"
    },
    {
        "source": "frontend/components/ui/component_35.tsx",
        "target": "frontend/components/ui/component_15.tsx"
    },
    {
        "source": "backend/parser/ast_parser_35.py",
        "target": "backend/parser/ast_parser_36.py"
    },
    {
        "source": "backend/rag/vector_service_24.py",
        "target": "backend/rag/vector_service_11.py"
    },
    {
        "source": "utils/helpers/standalone_util_24.py",
        "target": "utils/helpers/standalone_util_25.py"
    },
    {
        "source": "backend/database/model_31.py",
        "target": "backend/database/model_14.py"
    },
    {
        "source": "backend/database/model_08.py",
        "target": "backend/database/model_09.py"
    },
    {
        "source": "frontend/components/ui/component_27.tsx",
        "target": "frontend/components/ui/component_39.tsx"
    },
    {
        "source": "backend/graph/graph_engine_40.py",
        "target": "backend/graph/graph_engine_41.py"
    },
    {
        "source": "utils/helpers/standalone_util_20.py",
        "target": "utils/helpers/standalone_util_21.py"
    },
    {
        "source": "backend/database/model_05.py",
        "target": "backend/database/model_06.py"
    },
    {
        "source": "backend/rag/vector_service_13.py",
        "target": "backend/rag/vector_service_14.py"
    },
    {
        "source": "backend/api/route_39.py",
        "target": "backend/api/route_40.py"
    },
    {
        "source": "backend/api/route_11.py",
        "target": "backend/api/route_35.py"
    },
    {
        "source": "backend/rag/vector_service_19.py",
        "target": "backend/rag/vector_service_20.py"
    },
    {
        "source": "frontend/components/ui/component_05.tsx",
        "target": "frontend/components/ui/component_04.tsx"
    },
    {
        "source": "backend/parser/ast_parser_44.py",
        "target": "backend/parser/ast_parser_35.py"
    },
    {
        "source": "frontend/components/ui/component_11.tsx",
        "target": "frontend/components/ui/component_20.tsx"
    },
    {
        "source": "frontend/components/ui/component_14.tsx",
        "target": "backend/parser/ast_parser_29.py"
    },
    {
        "source": "backend/security/scanner_04.py",
        "target": "backend/security/scanner_05.py"
    },
    {
        "source": "backend/api/route_08.py",
        "target": "backend/api/route_25.py"
    },
    {
        "source": "frontend/components/ui/component_11.tsx",
        "target": "frontend/components/ui/component_16.tsx"
    },
    {
        "source": "frontend/components/ui/component_43.tsx",
        "target": "frontend/components/ui/component_13.tsx"
    },
    {
        "source": "backend/api/route_21.py",
        "target": "backend/api/route_22.py"
    },
    {
        "source": "backend/api/route_24.py",
        "target": "backend/api/route_37.py"
    },
    {
        "source": "utils/helpers/standalone_util_13.py",
        "target": "utils/helpers/standalone_util_14.py"
    },
    {
        "source": "backend/security/scanner_16.py",
        "target": "backend/security/scanner_08.py"
    },
    {
        "source": "backend/parser/ast_parser_26.py",
        "target": "backend/parser/ast_parser_22.py"
    },
    {
        "source": "backend/graph/graph_engine_30.py",
        "target": "backend/graph/graph_engine_31.py"
    },
    {
        "source": "backend/api/route_30.py",
        "target": "backend/api/route_10.py"
    },
    {
        "source": "backend/database/model_19.py",
        "target": "backend/database/model_28.py"
    },
    {
        "source": "frontend/components/ui/component_32.tsx",
        "target": "frontend/components/ui/component_05.tsx"
    },
    {
        "source": "frontend/components/ui/component_35.tsx",
        "target": "backend/parser/ast_parser_42.py"
    },
    {
        "source": "backend/api/route_28.py",
        "target": "backend/api/route_39.py"
    },
    {
        "source": "backend/rag/vector_service_43.py",
        "target": "backend/api/route_34.py"
    },
    {
        "source": "backend/rag/vector_service_06.py",
        "target": "backend/rag/vector_service_07.py"
    },
    {
        "source": "backend/parser/ast_parser_42.py",
        "target": "backend/graph/graph_engine_02.py"
    },
    {
        "source": "backend/graph/graph_engine_25.py",
        "target": "backend/graph/graph_engine_27.py"
    },
    {
        "source": "backend/rag/vector_service_23.py",
        "target": "backend/rag/vector_service_35.py"
    },
    {
        "source": "backend/api/route_29.py",
        "target": "backend/api/route_30.py"
    },
    {
        "source": "backend/graph/graph_engine_33.py",
        "target": "backend/graph/graph_engine_28.py"
    },
    {
        "source": "backend/rag/vector_service_19.py",
        "target": "backend/rag/vector_service_31.py"
    },
    {
        "source": "frontend/components/ui/component_35.tsx",
        "target": "frontend/components/ui/component_30.tsx"
    },
    {
        "source": "backend/parser/ast_parser_42.py",
        "target": "backend/parser/ast_parser_43.py"
    },
    {
        "source": "frontend/components/ui/component_34.tsx",
        "target": "frontend/components/ui/component_25.tsx"
    },
    {
        "source": "backend/graph/graph_engine_35.py",
        "target": "backend/graph/graph_engine_30.py"
    },
    {
        "source": "backend/rag/vector_service_20.py",
        "target": "backend/rag/vector_service_21.py"
    },
    {
        "source": "backend/parser/ast_parser_44.py",
        "target": "backend/database/model_31.py"
    },
    {
        "source": "backend/rag/vector_service_30.py",
        "target": "backend/rag/vector_service_37.py"
    },
    {
        "source": "backend/api/route_04.py",
        "target": "backend/api/route_08.py"
    },
    {
        "source": "backend/graph/graph_engine_21.py",
        "target": "backend/graph/graph_engine_30.py"
    },
    {
        "source": "backend/parser/ast_parser_45.py",
        "target": "backend/parser/ast_parser_10.py"
    },
    {
        "source": "backend/database/model_30.py",
        "target": "backend/security/scanner_09.py"
    },
    {
        "source": "backend/rag/vector_service_37.py",
        "target": "backend/rag/vector_service_38.py"
    },
    {
        "source": "backend/database/model_11.py",
        "target": "backend/database/model_12.py"
    },
    {
        "source": "backend/parser/ast_parser_48.py",
        "target": "backend/parser/ast_parser_49.py"
    },
    {
        "source": "backend/parser/ast_parser_17.py",
        "target": "backend/parser/ast_parser_03.py"
    },
    {
        "source": "backend/parser/ast_parser_35.py",
        "target": "backend/parser/ast_parser_14.py"
    },
    {
        "source": "backend/rag/vector_service_14.py",
        "target": "backend/rag/vector_service_15.py"
    },
    {
        "source": "backend/rag/vector_service_20.py",
        "target": "backend/rag/vector_service_01.py"
    },
    {
        "source": "backend/api/route_10.py",
        "target": "backend/api/route_11.py"
    },
    {
        "source": "frontend/components/ui/component_39.tsx",
        "target": "frontend/components/ui/component_48.tsx"
    },
    {
        "source": "utils/helpers/standalone_util_14.py",
        "target": "utils/helpers/standalone_util_15.py"
    },
    {
        "source": "backend/parser/ast_parser_16.py",
        "target": "backend/parser/ast_parser_17.py"
    },
    {
        "source": "backend/api/route_22.py",
        "target": "backend/api/route_23.py"
    },
    {
        "source": "backend/graph/graph_engine_28.py",
        "target": "backend/graph/graph_engine_29.py"
    },
    {
        "source": "backend/graph/graph_engine_17.py",
        "target": "backend/graph/graph_engine_06.py"
    },
    {
        "source": "frontend/components/ui/component_03.tsx",
        "target": "frontend/components/ui/component_04.tsx"
    },
    {
        "source": "frontend/components/ui/component_22.tsx",
        "target": "frontend/components/ui/component_12.tsx"
    },
    {
        "source": "backend/security/scanner_02.py",
        "target": "backend/security/scanner_11.py"
    },
    {
        "source": "backend/api/route_18.py",
        "target": "backend/api/route_19.py"
    },
    {
        "source": "backend/parser/ast_parser_47.py",
        "target": "backend/parser/ast_parser_21.py"
    },
    {
        "source": "backend/api/route_35.py",
        "target": "backend/api/route_17.py"
    },
    {
        "source": "backend/graph/graph_engine_31.py",
        "target": "backend/graph/graph_engine_40.py"
    },
    {
        "source": "backend/rag/vector_service_07.py",
        "target": "backend/rag/vector_service_28.py"
    },
    {
        "source": "frontend/components/ui/component_03.tsx",
        "target": "frontend/components/ui/component_30.tsx"
    },
    {
        "source": "backend/graph/graph_engine_35.py",
        "target": "backend/graph/graph_engine_39.py"
    },
    {
        "source": "backend/security/scanner_09.py",
        "target": "backend/security/scanner_10.py"
    },
    {
        "source": "backend/graph/graph_engine_17.py",
        "target": "frontend/components/ui/component_30.tsx"
    },
    {
        "source": "backend/database/model_08.py",
        "target": "backend/database/model_37.py"
    },
    {
        "source": "backend/rag/vector_service_38.py",
        "target": "backend/rag/vector_service_34.py"
    },
    {
        "source": "backend/rag/vector_service_33.py",
        "target": "backend/rag/vector_service_34.py"
    },
    {
        "source": "frontend/components/ui/component_02.tsx",
        "target": "frontend/components/ui/component_06.tsx"
    },
    {
        "source": "backend/graph/graph_engine_44.py",
        "target": "backend/graph/graph_engine_20.py"
    },
    {
        "source": "backend/rag/vector_service_02.py",
        "target": "backend/rag/vector_service_06.py"
    },
    {
        "source": "backend/database/model_37.py",
        "target": "backend/database/model_38.py"
    },
    {
        "source": "backend/security/scanner_03.py",
        "target": "backend/security/scanner_08.py"
    },
    {
        "source": "frontend/components/ui/component_42.tsx",
        "target": "frontend/components/ui/component_29.tsx"
    },
    {
        "source": "utils/helpers/standalone_util_01.py",
        "target": "backend/api/route_01.py"
    },
    {
        "source": "frontend/components/ui/component_30.tsx",
        "target": "frontend/components/ui/component_31.tsx"
    },
    {
        "source": "backend/api/route_16.py",
        "target": "backend/api/route_17.py"
    },
    {
        "source": "backend/parser/ast_parser_21.py",
        "target": "backend/parser/ast_parser_26.py"
    },
    {
        "source": "utils/helpers/standalone_util_08.py",
        "target": "utils/helpers/standalone_util_09.py"
    },
    {
        "source": "backend/database/model_28.py",
        "target": "backend/database/model_29.py"
    },
    {
        "source": "backend/database/model_31.py",
        "target": "backend/database/model_36.py"
    },
    {
        "source": "backend/parser/ast_parser_26.py",
        "target": "backend/parser/ast_parser_27.py"
    },
    {
        "source": "backend/graph/graph_engine_36.py",
        "target": "backend/graph/graph_engine_29.py"
    },
    {
        "source": "backend/database/model_07.py",
        "target": "backend/database/model_08.py"
    },
    {
        "source": "backend/parser/ast_parser_36.py",
        "target": "backend/parser/ast_parser_01.py"
    },
    {
        "source": "frontend/components/ui/component_19.tsx",
        "target": "backend/graph/graph_engine_15.py"
    },
    {
        "source": "backend/graph/graph_engine_02.py",
        "target": "backend/graph/graph_engine_25.py"
    },
    {
        "source": "backend/database/model_41.py",
        "target": "backend/database/model_04.py"
    },
    {
        "source": "backend/graph/graph_engine_03.py",
        "target": "backend/graph/graph_engine_04.py"
    },
    {
        "source": "backend/parser/ast_parser_32.py",
        "target": "backend/parser/ast_parser_17.py"
    },
    {
        "source": "frontend/components/ui/component_42.tsx",
        "target": "frontend/components/ui/component_43.tsx"
    },
    {
        "source": "frontend/components/ui/component_06.tsx",
        "target": "frontend/components/ui/component_21.tsx"
    },
    {
        "source": "frontend/components/ui/component_14.tsx",
        "target": "frontend/components/ui/component_17.tsx"
    },
    {
        "source": "backend/parser/ast_parser_12.py",
        "target": "backend/parser/ast_parser_38.py"
    },
    {
        "source": "backend/database/model_26.py",
        "target": "backend/database/model_27.py"
    },
    {
        "source": "backend/database/model_28.py",
        "target": "backend/database/model_14.py"
    },
    {
        "source": "backend/database/model_30.py",
        "target": "backend/database/model_04.py"
    },
    {
        "source": "backend/parser/ast_parser_33.py",
        "target": "backend/parser/ast_parser_17.py"
    },
    {
        "source": "backend/graph/graph_engine_05.py",
        "target": "backend/graph/graph_engine_27.py"
    },
    {
        "source": "backend/rag/vector_service_07.py",
        "target": "backend/rag/vector_service_13.py"
    },
    {
        "source": "backend/security/scanner_14.py",
        "target": "backend/database/model_29.py"
    },
    {
        "source": "backend/rag/vector_service_02.py",
        "target": "backend/rag/vector_service_32.py"
    },
    {
        "source": "backend/database/model_38.py",
        "target": "backend/database/model_39.py"
    },
    {
        "source": "backend/database/model_36.py",
        "target": "backend/database/model_37.py"
    },
    {
        "source": "backend/rag/vector_service_32.py",
        "target": "backend/rag/vector_service_33.py"
    },
    {
        "source": "backend/rag/vector_service_25.py",
        "target": "backend/database/model_30.py"
    },
    {
        "source": "backend/rag/vector_service_24.py",
        "target": "backend/rag/vector_service_25.py"
    },
    {
        "source": "frontend/components/ui/component_32.tsx",
        "target": "backend/api/route_29.py"
    },
    {
        "source": "backend/graph/graph_engine_44.py",
        "target": "backend/graph/graph_engine_45.py"
    },
    {
        "source": "backend/parser/ast_parser_09.py",
        "target": "backend/parser/ast_parser_23.py"
    },
    {
        "source": "frontend/components/ui/component_36.tsx",
        "target": "frontend/components/ui/component_01.tsx"
    },
    {
        "source": "backend/security/scanner_10.py",
        "target": "backend/security/scanner_20.py"
    },
    {
        "source": "backend/api/route_33.py",
        "target": "backend/api/route_12.py"
    },
    {
        "source": "backend/api/route_03.py",
        "target": "frontend/components/ui/component_20.tsx"
    },
    {
        "source": "frontend/components/ui/component_49.tsx",
        "target": "frontend/components/ui/component_04.tsx"
    },
    {
        "source": "backend/parser/ast_parser_13.py",
        "target": "backend/parser/ast_parser_17.py"
    },
    {
        "source": "backend/rag/vector_service_45.py",
        "target": "backend/rag/vector_service_17.py"
    },
    {
        "source": "backend/api/route_19.py",
        "target": "backend/api/route_20.py"
    },
    {
        "source": "frontend/components/ui/component_16.tsx",
        "target": "frontend/components/ui/component_46.tsx"
    },
    {
        "source": "backend/rag/vector_service_16.py",
        "target": "backend/rag/vector_service_17.py"
    },
    {
        "source": "backend/api/route_04.py",
        "target": "backend/parser/ast_parser_19.py"
    },
    {
        "source": "backend/database/model_34.py",
        "target": "backend/database/model_35.py"
    },
    {
        "source": "backend/parser/ast_parser_08.py",
        "target": "backend/database/model_43.py"
    },
    {
        "source": "backend/database/model_20.py",
        "target": "backend/database/model_16.py"
    },
    {
        "source": "backend/parser/ast_parser_48.py",
        "target": "backend/security/scanner_14.py"
    },
    {
        "source": "backend/rag/vector_service_06.py",
        "target": "backend/rag/vector_service_18.py"
    },
    {
        "source": "backend/api/route_20.py",
        "target": "backend/api/route_21.py"
    },
    {
        "source": "backend/security/scanner_05.py",
        "target": "backend/security/scanner_03.py"
    },
    {
        "source": "backend/graph/graph_engine_03.py",
        "target": "backend/rag/vector_service_40.py"
    },
    {
        "source": "backend/api/route_08.py",
        "target": "backend/api/route_02.py"
    },
    {
        "source": "backend/api/route_24.py",
        "target": "backend/api/route_15.py"
    },
    {
        "source": "backend/api/route_06.py",
        "target": "backend/security/scanner_03.py"
    },
    {
        "source": "backend/graph/graph_engine_42.py",
        "target": "backend/graph/graph_engine_43.py"
    },
    {
        "source": "backend/database/model_11.py",
        "target": "backend/database/model_17.py"
    },
    {
        "source": "backend/rag/vector_service_12.py",
        "target": "backend/rag/vector_service_13.py"
    },
    {
        "source": "backend/database/model_33.py",
        "target": "backend/database/model_34.py"
    },
    {
        "source": "backend/api/route_35.py",
        "target": "backend/api/route_16.py"
    },
    {
        "source": "backend/database/model_39.py",
        "target": "backend/database/model_40.py"
    },
    {
        "source": "backend/database/model_42.py",
        "target": "backend/database/model_24.py"
    },
    {
        "source": "backend/parser/ast_parser_24.py",
        "target": "backend/parser/ast_parser_25.py"
    },
    {
        "source": "backend/database/model_26.py",
        "target": "backend/database/model_04.py"
    },
    {
        "source": "backend/parser/ast_parser_18.py",
        "target": "backend/parser/ast_parser_03.py"
    },
    {
        "source": "backend/graph/graph_engine_15.py",
        "target": "backend/graph/graph_engine_18.py"
    },
    {
        "source": "backend/graph/graph_engine_18.py",
        "target": "backend/graph/graph_engine_27.py"
    },
    {
        "source": "frontend/components/ui/component_26.tsx",
        "target": "frontend/components/ui/component_27.tsx"
    },
    {
        "source": "backend/rag/vector_service_29.py",
        "target": "backend/rag/vector_service_16.py"
    },
    {
        "source": "frontend/components/ui/component_49.tsx",
        "target": "frontend/components/ui/component_50.tsx"
    },
    {
        "source": "backend/graph/graph_engine_43.py",
        "target": "backend/graph/graph_engine_06.py"
    },
    {
        "source": "frontend/components/ui/component_15.tsx",
        "target": "frontend/components/ui/component_17.tsx"
    },
    {
        "source": "backend/rag/vector_service_14.py",
        "target": "backend/rag/vector_service_30.py"
    },
    {
        "source": "frontend/components/ui/component_39.tsx",
        "target": "frontend/components/ui/component_31.tsx"
    },
    {
        "source": "backend/graph/graph_engine_41.py",
        "target": "backend/graph/graph_engine_42.py"
    },
    {
        "source": "backend/database/model_30.py",
        "target": "backend/database/model_31.py"
    },
    {
        "source": "backend/graph/graph_engine_04.py",
        "target": "backend/graph/graph_engine_05.py"
    },
    {
        "source": "backend/graph/graph_engine_12.py",
        "target": "backend/graph/graph_engine_13.py"
    },
    {
        "source": "frontend/components/ui/component_36.tsx",
        "target": "frontend/components/ui/component_49.tsx"
    },
    {
        "source": "backend/parser/ast_parser_28.py",
        "target": "backend/security/scanner_05.py"
    },
    {
        "source": "backend/parser/ast_parser_46.py",
        "target": "frontend/components/ui/component_49.tsx"
    },
    {
        "source": "backend/database/model_02.py",
        "target": "backend/database/model_38.py"
    },
    {
        "source": "backend/security/scanner_16.py",
        "target": "backend/security/scanner_10.py"
    },
    {
        "source": "backend/database/model_06.py",
        "target": "backend/database/model_12.py"
    },
    {
        "source": "frontend/components/ui/component_44.tsx",
        "target": "frontend/components/ui/component_45.tsx"
    },
    {
        "source": "backend/api/route_17.py",
        "target": "backend/api/route_03.py"
    },
    {
        "source": "backend/parser/ast_parser_12.py",
        "target": "backend/parser/ast_parser_40.py"
    },
    {
        "source": "backend/database/model_28.py",
        "target": "backend/database/model_23.py"
    },
    {
        "source": "frontend/components/ui/component_40.tsx",
        "target": "frontend/components/ui/component_48.tsx"
    },
    {
        "source": "utils/helpers/standalone_util_19.py",
        "target": "utils/helpers/standalone_util_20.py"
    },
    {
        "source": "backend/api/route_07.py",
        "target": "backend/api/route_35.py"
    },
    {
        "source": "backend/rag/vector_service_28.py",
        "target": "backend/rag/vector_service_12.py"
    },
    {
        "source": "frontend/components/ui/component_43.tsx",
        "target": "frontend/components/ui/component_06.tsx"
    },
    {
        "source": "backend/rag/vector_service_16.py",
        "target": "backend/rag/vector_service_27.py"
    },
    {
        "source": "backend/security/scanner_05.py",
        "target": "frontend/components/ui/component_41.tsx"
    },
    {
        "source": "backend/graph/graph_engine_34.py",
        "target": "backend/graph/graph_engine_30.py"
    },
    {
        "source": "backend/database/model_43.py",
        "target": "backend/database/model_42.py"
    },
    {
        "source": "backend/graph/graph_engine_16.py",
        "target": "backend/graph/graph_engine_17.py"
    },
    {
        "source": "frontend/components/ui/component_43.tsx",
        "target": "frontend/components/ui/component_07.tsx"
    },
    {
        "source": "backend/database/model_22.py",
        "target": "backend/database/model_23.py"
    },
    {
        "source": "backend/database/model_14.py",
        "target": "backend/database/model_35.py"
    },
    {
        "source": "backend/rag/vector_service_36.py",
        "target": "backend/rag/vector_service_37.py"
    },
    {
        "source": "backend/api/route_11.py",
        "target": "backend/api/route_30.py"
    },
    {
        "source": "backend/rag/vector_service_02.py",
        "target": "backend/rag/vector_service_16.py"
    },
    {
        "source": "backend/api/route_34.py",
        "target": "backend/api/route_35.py"
    },
    {
        "source": "backend/parser/ast_parser_44.py",
        "target": "backend/parser/ast_parser_48.py"
    },
    {
        "source": "backend/rag/vector_service_42.py",
        "target": "frontend/components/ui/component_36.tsx"
    },
    {
        "source": "backend/parser/ast_parser_08.py",
        "target": "backend/parser/ast_parser_17.py"
    },
    {
        "source": "backend/database/model_05.py",
        "target": "backend/database/model_44.py"
    },
    {
        "source": "backend/rag/vector_service_30.py",
        "target": "backend/parser/ast_parser_33.py"
    },
    {
        "source": "backend/graph/graph_engine_35.py",
        "target": "backend/graph/graph_engine_36.py"
    },
    {
        "source": "backend/parser/ast_parser_18.py",
        "target": "backend/parser/ast_parser_19.py"
    },
    {
        "source": "backend/security/scanner_15.py",
        "target": "backend/security/scanner_18.py"
    },
    {
        "source": "frontend/components/ui/component_32.tsx",
        "target": "frontend/components/ui/component_29.tsx"
    },
    {
        "source": "backend/database/model_16.py",
        "target": "backend/database/model_05.py"
    },
    {
        "source": "backend/parser/ast_parser_24.py",
        "target": "backend/parser/ast_parser_03.py"
    },
    {
        "source": "backend/database/model_35.py",
        "target": "backend/database/model_45.py"
    },
    {
        "source": "backend/api/route_21.py",
        "target": "backend/api/route_14.py"
    },
    {
        "source": "backend/rag/vector_service_38.py",
        "target": "backend/rag/vector_service_39.py"
    },
    {
        "source": "frontend/components/ui/component_43.tsx",
        "target": "frontend/components/ui/component_44.tsx"
    },
    {
        "source": "frontend/components/ui/component_05.tsx",
        "target": "frontend/components/ui/component_44.tsx"
    },
    {
        "source": "backend/graph/graph_engine_15.py",
        "target": "backend/graph/graph_engine_13.py"
    },
    {
        "source": "backend/parser/ast_parser_20.py",
        "target": "backend/parser/ast_parser_21.py"
    },
    {
        "source": "frontend/components/ui/component_41.tsx",
        "target": "frontend/components/ui/component_38.tsx"
    },
    {
        "source": "backend/rag/vector_service_27.py",
        "target": "backend/rag/vector_service_32.py"
    },
    {
        "source": "backend/api/route_21.py",
        "target": "backend/security/scanner_20.py"
    },
    {
        "source": "backend/graph/graph_engine_38.py",
        "target": "backend/graph/graph_engine_39.py"
    },
    {
        "source": "utils/helpers/standalone_util_06.py",
        "target": "backend/database/model_01.py"
    },
    {
        "source": "frontend/components/ui/component_16.tsx",
        "target": "frontend/components/ui/component_17.tsx"
    },
    {
        "source": "backend/rag/vector_service_04.py",
        "target": "backend/api/route_22.py"
    },
    {
        "source": "backend/api/route_04.py",
        "target": "backend/rag/vector_service_39.py"
    },
    {
        "source": "backend/graph/graph_engine_25.py",
        "target": "backend/graph/graph_engine_26.py"
    },
    {
        "source": "frontend/components/ui/component_38.tsx",
        "target": "frontend/components/ui/component_28.tsx"
    },
    {
        "source": "backend/parser/ast_parser_08.py",
        "target": "backend/parser/ast_parser_09.py"
    },
    {
        "source": "backend/rag/vector_service_07.py",
        "target": "backend/rag/vector_service_38.py"
    },
    {
        "source": "backend/security/scanner_04.py",
        "target": "backend/security/scanner_17.py"
    },
    {
        "source": "frontend/components/ui/component_29.tsx",
        "target": "frontend/components/ui/component_08.tsx"
    },
    {
        "source": "backend/rag/vector_service_13.py",
        "target": "backend/rag/vector_service_21.py"
    },
    {
        "source": "utils/helpers/standalone_util_03.py",
        "target": "utils/helpers/standalone_util_04.py"
    },
    {
        "source": "backend/security/scanner_07.py",
        "target": "backend/parser/ast_parser_25.py"
    },
    {
        "source": "backend/parser/ast_parser_28.py",
        "target": "backend/parser/ast_parser_29.py"
    },
    {
        "source": "backend/rag/vector_service_08.py",
        "target": "backend/rag/vector_service_37.py"
    },
    {
        "source": "frontend/components/ui/component_08.tsx",
        "target": "frontend/components/ui/component_02.tsx"
    },
    {
        "source": "backend/graph/graph_engine_20.py",
        "target": "backend/graph/graph_engine_21.py"
    },
    {
        "source": "frontend/components/ui/component_26.tsx",
        "target": "frontend/components/ui/component_33.tsx"
    },
    {
        "source": "backend/graph/graph_engine_33.py",
        "target": "backend/parser/ast_parser_38.py"
    },
    {
        "source": "backend/rag/vector_service_18.py",
        "target": "backend/graph/graph_engine_03.py"
    },
    {
        "source": "backend/parser/ast_parser_35.py",
        "target": "backend/parser/ast_parser_03.py"
    },
    {
        "source": "backend/parser/ast_parser_25.py",
        "target": "backend/parser/ast_parser_37.py"
    },
    {
        "source": "frontend/components/ui/component_38.tsx",
        "target": "frontend/components/ui/component_39.tsx"
    },
    {
        "source": "backend/database/model_26.py",
        "target": "backend/database/model_43.py"
    },
    {
        "source": "backend/database/model_37.py",
        "target": "backend/security/scanner_07.py"
    },
    {
        "source": "backend/api/route_17.py",
        "target": "backend/api/route_36.py"
    },
    {
        "source": "backend/database/model_42.py",
        "target": "backend/database/model_43.py"
    },
    {
        "source": "backend/security/scanner_02.py",
        "target": "backend/security/scanner_03.py"
    },
    {
        "source": "frontend/components/ui/component_02.tsx",
        "target": "frontend/components/ui/component_49.tsx"
    },
    {
        "source": "backend/parser/ast_parser_36.py",
        "target": "backend/parser/ast_parser_20.py"
    },
    {
        "source": "backend/api/route_03.py",
        "target": "backend/api/route_15.py"
    },
    {
        "source": "backend/api/route_14.py",
        "target": "backend/api/route_15.py"
    },
    {
        "source": "backend/database/model_17.py",
        "target": "backend/database/model_30.py"
    },
    {
        "source": "backend/parser/ast_parser_24.py",
        "target": "backend/parser/ast_parser_19.py"
    },
    {
        "source": "backend/security/scanner_11.py",
        "target": "backend/parser/ast_parser_08.py"
    },
    {
        "source": "backend/database/model_42.py",
        "target": "backend/database/model_07.py"
    },
    {
        "source": "backend/database/model_45.py",
        "target": "backend/database/model_36.py"
    },
    {
        "source": "backend/graph/graph_engine_43.py",
        "target": "backend/parser/ast_parser_17.py"
    },
    {
        "source": "backend/database/model_24.py",
        "target": "backend/database/model_25.py"
    },
    {
        "source": "backend/database/model_18.py",
        "target": "backend/database/model_30.py"
    },
    {
        "source": "backend/api/route_15.py",
        "target": "backend/api/route_03.py"
    },
    {
        "source": "backend/security/scanner_19.py",
        "target": "backend/security/scanner_13.py"
    },
    {
        "source": "backend/security/scanner_05.py",
        "target": "backend/database/model_35.py"
    },
    {
        "source": "backend/database/model_40.py",
        "target": "backend/database/model_06.py"
    },
    {
        "source": "frontend/components/ui/component_18.tsx",
        "target": "frontend/components/ui/component_10.tsx"
    },
    {
        "source": "backend/parser/ast_parser_24.py",
        "target": "backend/rag/vector_service_08.py"
    },
    {
        "source": "backend/security/scanner_04.py",
        "target": "backend/security/scanner_15.py"
    },
    {
        "source": "backend/database/model_44.py",
        "target": "backend/database/model_42.py"
    },
    {
        "source": "frontend/components/ui/component_12.tsx",
        "target": "frontend/components/ui/component_13.tsx"
    },
    {
        "source": "backend/security/scanner_18.py",
        "target": "backend/security/scanner_14.py"
    },
    {
        "source": "utils/helpers/standalone_util_11.py",
        "target": "utils/helpers/standalone_util_12.py"
    },
    {
        "source": "backend/security/scanner_15.py",
        "target": "backend/security/scanner_11.py"
    },
    {
        "source": "backend/graph/graph_engine_29.py",
        "target": "backend/graph/graph_engine_40.py"
    },
    {
        "source": "backend/parser/ast_parser_14.py",
        "target": "backend/parser/ast_parser_15.py"
    },
    {
        "source": "backend/database/model_07.py",
        "target": "backend/database/model_04.py"
    },
    {
        "source": "backend/security/scanner_19.py",
        "target": "backend/parser/ast_parser_15.py"
    },
    {
        "source": "frontend/components/ui/component_46.tsx",
        "target": "frontend/components/ui/component_47.tsx"
    },
    {
        "source": "backend/api/route_19.py",
        "target": "backend/api/route_28.py"
    },
    {
        "source": "backend/database/model_18.py",
        "target": "backend/database/model_19.py"
    },
    {
        "source": "frontend/components/ui/component_31.tsx",
        "target": "frontend/components/ui/component_32.tsx"
    },
    {
        "source": "frontend/components/ui/component_19.tsx",
        "target": "frontend/components/ui/component_29.tsx"
    },
    {
        "source": "frontend/components/ui/component_37.tsx",
        "target": "frontend/components/ui/component_19.tsx"
    },
    {
        "source": "backend/graph/graph_engine_18.py",
        "target": "backend/graph/graph_engine_22.py"
    },
    {
        "source": "backend/parser/ast_parser_08.py",
        "target": "backend/parser/ast_parser_05.py"
    },
    {
        "source": "backend/security/scanner_14.py",
        "target": "backend/security/scanner_16.py"
    },
    {
        "source": "backend/api/route_02.py",
        "target": "backend/database/model_06.py"
    },
    {
        "source": "backend/rag/vector_service_24.py",
        "target": "backend/rag/vector_service_05.py"
    },
    {
        "source": "backend/security/scanner_18.py",
        "target": "frontend/components/ui/component_25.tsx"
    },
    {
        "source": "backend/parser/ast_parser_45.py",
        "target": "backend/parser/ast_parser_19.py"
    },
    {
        "source": "backend/api/route_03.py",
        "target": "backend/api/route_04.py"
    },
    {
        "source": "backend/graph/graph_engine_42.py",
        "target": "backend/graph/graph_engine_28.py"
    },
    {
        "source": "backend/parser/ast_parser_28.py",
        "target": "backend/parser/ast_parser_39.py"
    },
    {
        "source": "backend/api/route_09.py",
        "target": "backend/api/route_33.py"
    },
    {
        "source": "backend/database/model_34.py",
        "target": "backend/database/model_11.py"
    },
    {
        "source": "frontend/components/ui/component_09.tsx",
        "target": "frontend/components/ui/component_10.tsx"
    },
    {
        "source": "backend/parser/ast_parser_15.py",
        "target": "backend/parser/ast_parser_16.py"
    },
    {
        "source": "backend/rag/vector_service_18.py",
        "target": "backend/rag/vector_service_19.py"
    },
    {
        "source": "backend/graph/graph_engine_21.py",
        "target": "backend/graph/graph_engine_22.py"
    },
    {
        "source": "backend/parser/ast_parser_11.py",
        "target": "backend/parser/ast_parser_29.py"
    },
    {
        "source": "backend/database/model_31.py",
        "target": "backend/database/model_32.py"
    },
    {
        "source": "backend/api/route_24.py",
        "target": "backend/api/route_25.py"
    },
    {
        "source": "backend/api/route_38.py",
        "target": "backend/api/route_28.py"
    },
    {
        "source": "backend/database/model_21.py",
        "target": "backend/database/model_22.py"
    },
    {
        "source": "backend/security/scanner_05.py",
        "target": "backend/security/scanner_17.py"
    },
    {
        "source": "backend/database/model_09.py",
        "target": "backend/database/model_37.py"
    },
    {
        "source": "backend/database/model_29.py",
        "target": "backend/database/model_08.py"
    },
    {
        "source": "backend/parser/ast_parser_40.py",
        "target": "backend/parser/ast_parser_48.py"
    },
    {
        "source": "backend/parser/ast_parser_18.py",
        "target": "backend/parser/ast_parser_05.py"
    },
    {
        "source": "backend/parser/ast_parser_09.py",
        "target": "backend/parser/ast_parser_10.py"
    },
    {
        "source": "backend/parser/ast_parser_40.py",
        "target": "backend/parser/ast_parser_21.py"
    },
    {
        "source": "backend/parser/ast_parser_08.py",
        "target": "backend/parser/ast_parser_07.py"
    },
    {
        "source": "backend/graph/graph_engine_05.py",
        "target": "backend/graph/graph_engine_06.py"
    },
    {
        "source": "backend/parser/ast_parser_42.py",
        "target": "backend/parser/ast_parser_34.py"
    },
    {
        "source": "frontend/components/ui/component_23.tsx",
        "target": "frontend/components/ui/component_24.tsx"
    },
    {
        "source": "frontend/components/ui/component_31.tsx",
        "target": "frontend/components/ui/component_34.tsx"
    },
    {
        "source": "frontend/components/ui/component_23.tsx",
        "target": "frontend/components/ui/component_27.tsx"
    },
    {
        "source": "frontend/components/ui/component_45.tsx",
        "target": "frontend/components/ui/component_32.tsx"
    },
    {
        "source": "backend/graph/graph_engine_07.py",
        "target": "frontend/components/ui/component_32.tsx"
    },
    {
        "source": "backend/graph/graph_engine_29.py",
        "target": "backend/graph/graph_engine_05.py"
    },
    {
        "source": "backend/rag/vector_service_02.py",
        "target": "backend/rag/vector_service_20.py"
    },
    {
        "source": "frontend/components/ui/component_17.tsx",
        "target": "frontend/components/ui/component_18.tsx"
    },
    {
        "source": "backend/database/model_06.py",
        "target": "backend/database/model_07.py"
    },
    {
        "source": "backend/api/route_19.py",
        "target": "backend/api/route_06.py"
    },
    {
        "source": "backend/api/route_17.py",
        "target": "backend/api/route_09.py"
    },
    {
        "source": "backend/parser/ast_parser_27.py",
        "target": "frontend/components/ui/component_08.tsx"
    },
    {
        "source": "backend/database/model_20.py",
        "target": "backend/database/model_21.py"
    },
    {
        "source": "frontend/components/ui/component_40.tsx",
        "target": "frontend/components/ui/component_41.tsx"
    },
    {
        "source": "backend/parser/ast_parser_24.py",
        "target": "backend/parser/ast_parser_38.py"
    },
    {
        "source": "backend/database/model_08.py",
        "target": "backend/rag/vector_service_23.py"
    },
    {
        "source": "backend/graph/graph_engine_13.py",
        "target": "backend/graph/graph_engine_14.py"
    },
    {
        "source": "backend/parser/ast_parser_44.py",
        "target": "backend/parser/ast_parser_16.py"
    },
    {
        "source": "backend/graph/graph_engine_19.py",
        "target": "backend/graph/graph_engine_33.py"
    },
    {
        "source": "frontend/components/ui/component_27.tsx",
        "target": "frontend/components/ui/component_04.tsx"
    },
    {
        "source": "backend/parser/ast_parser_48.py",
        "target": "frontend/components/ui/component_44.tsx"
    },
    {
        "source": "backend/graph/graph_engine_18.py",
        "target": "backend/graph/graph_engine_19.py"
    },
    {
        "source": "frontend/components/ui/component_06.tsx",
        "target": "frontend/components/ui/component_39.tsx"
    },
    {
        "source": "utils/helpers/standalone_util_09.py",
        "target": "utils/helpers/standalone_util_10.py"
    },
    {
        "source": "backend/rag/vector_service_40.py",
        "target": "backend/rag/vector_service_10.py"
    },
    {
        "source": "backend/graph/graph_engine_34.py",
        "target": "backend/graph/graph_engine_36.py"
    },
    {
        "source": "backend/parser/ast_parser_38.py",
        "target": "backend/database/model_21.py"
    },
    {
        "source": "backend/parser/ast_parser_12.py",
        "target": "backend/parser/ast_parser_13.py"
    },
    {
        "source": "backend/api/route_30.py",
        "target": "frontend/components/ui/component_45.tsx"
    },
    {
        "source": "backend/graph/graph_engine_16.py",
        "target": "backend/graph/graph_engine_18.py"
    },
    {
        "source": "backend/api/route_05.py",
        "target": "backend/api/route_06.py"
    },
    {
        "source": "backend/rag/vector_service_23.py",
        "target": "backend/rag/vector_service_45.py"
    },
    {
        "source": "backend/parser/ast_parser_28.py",
        "target": "backend/parser/ast_parser_09.py"
    },
    {
        "source": "backend/rag/vector_service_41.py",
        "target": "backend/rag/vector_service_16.py"
    },
    {
        "source": "backend/parser/ast_parser_47.py",
        "target": "backend/security/scanner_11.py"
    },
    {
        "source": "backend/database/model_16.py",
        "target": "backend/database/model_13.py"
    },
    {
        "source": "backend/rag/vector_service_25.py",
        "target": "backend/rag/vector_service_26.py"
    },
    {
        "source": "backend/rag/vector_service_30.py",
        "target": "backend/rag/vector_service_10.py"
    },
    {
        "source": "backend/parser/ast_parser_36.py",
        "target": "backend/parser/ast_parser_10.py"
    },
    {
        "source": "frontend/components/ui/component_14.tsx",
        "target": "frontend/components/ui/component_41.tsx"
    },
    {
        "source": "backend/security/scanner_01.py",
        "target": "backend/security/scanner_02.py"
    },
    {
        "source": "backend/parser/ast_parser_48.py",
        "target": "backend/parser/ast_parser_43.py"
    },
    {
        "source": "frontend/components/ui/component_20.tsx",
        "target": "frontend/components/ui/component_37.tsx"
    },
    {
        "source": "backend/security/scanner_05.py",
        "target": "backend/security/scanner_06.py"
    },
    {
        "source": "utils/helpers/standalone_util_15.py",
        "target": "utils/helpers/standalone_util_16.py"
    },
    {
        "source": "backend/api/route_05.py",
        "target": "backend/api/route_25.py"
    },
    {
        "source": "frontend/components/ui/component_41.tsx",
        "target": "frontend/components/ui/component_42.tsx"
    },
    {
        "source": "backend/parser/ast_parser_01.py",
        "target": "backend/parser/ast_parser_22.py"
    },
    {
        "source": "backend/database/model_03.py",
        "target": "backend/database/model_04.py"
    },
    {
        "source": "backend/api/route_15.py",
        "target": "backend/api/route_07.py"
    },
    {
        "source": "backend/graph/graph_engine_39.py",
        "target": "backend/graph/graph_engine_21.py"
    },
    {
        "source": "backend/security/scanner_13.py",
        "target": "frontend/components/ui/component_36.tsx"
    },
    {
        "source": "backend/graph/graph_engine_22.py",
        "target": "backend/graph/graph_engine_23.py"
    },
    {
        "source": "backend/rag/vector_service_18.py",
        "target": "backend/rag/vector_service_36.py"
    },
    {
        "source": "frontend/components/ui/component_01.tsx",
        "target": "frontend/components/ui/component_02.tsx"
    },
    {
        "source": "backend/database/model_09.py",
        "target": "backend/api/route_18.py"
    },
    {
        "source": "backend/database/model_07.py",
        "target": "backend/database/model_43.py"
    },
    {
        "source": "backend/parser/ast_parser_50.py",
        "target": "backend/parser/ast_parser_18.py"
    },
    {
        "source": "backend/database/model_12.py",
        "target": "backend/database/model_13.py"
    },
    {
        "source": "backend/database/model_16.py",
        "target": "backend/database/model_17.py"
    },
    {
        "source": "backend/parser/ast_parser_43.py",
        "target": "backend/parser/ast_parser_08.py"
    },
    {
        "source": "backend/graph/graph_engine_31.py",
        "target": "backend/graph/graph_engine_11.py"
    },
    {
        "source": "utils/helpers/standalone_util_21.py",
        "target": "utils/helpers/standalone_util_22.py"
    },
    {
        "source": "backend/database/model_38.py",
        "target": "backend/database/model_15.py"
    },
    {
        "source": "backend/database/model_19.py",
        "target": "backend/database/model_14.py"
    },
    {
        "source": "backend/database/model_05.py",
        "target": "backend/database/model_35.py"
    },
    {
        "source": "frontend/components/ui/component_24.tsx",
        "target": "frontend/components/ui/component_25.tsx"
    },
    {
        "source": "frontend/components/ui/component_45.tsx",
        "target": "frontend/components/ui/component_46.tsx"
    },
    {
        "source": "frontend/components/ui/component_45.tsx",
        "target": "frontend/components/ui/component_30.tsx"
    },
    {
        "source": "backend/security/scanner_13.py",
        "target": "frontend/components/ui/component_18.tsx"
    },
    {
        "source": "backend/api/route_32.py",
        "target": "backend/api/route_06.py"
    },
    {
        "source": "frontend/components/ui/component_15.tsx",
        "target": "frontend/components/ui/component_16.tsx"
    },
    {
        "source": "backend/graph/graph_engine_31.py",
        "target": "backend/graph/graph_engine_01.py"
    },
    {
        "source": "backend/api/route_01.py",
        "target": "backend/api/route_08.py"
    },
    {
        "source": "backend/database/model_16.py",
        "target": "backend/database/model_31.py"
    },
    {
        "source": "backend/graph/graph_engine_23.py",
        "target": "backend/graph/graph_engine_15.py"
    },
    {
        "source": "frontend/components/ui/component_04.tsx",
        "target": "frontend/components/ui/component_05.tsx"
    },
    {
        "source": "backend/api/route_09.py",
        "target": "backend/api/route_10.py"
    },
    {
        "source": "backend/security/scanner_18.py",
        "target": "backend/security/scanner_13.py"
    },
    {
        "source": "backend/graph/graph_engine_09.py",
        "target": "backend/graph/graph_engine_40.py"
    },
    {
        "source": "backend/database/model_10.py",
        "target": "backend/database/model_13.py"
    },
    {
        "source": "backend/parser/ast_parser_47.py",
        "target": "backend/parser/ast_parser_48.py"
    },
    {
        "source": "backend/security/scanner_11.py",
        "target": "backend/security/scanner_18.py"
    },
    {
        "source": "backend/api/route_25.py",
        "target": "backend/rag/vector_service_40.py"
    },
    {
        "source": "backend/api/route_30.py",
        "target": "backend/api/route_24.py"
    },
    {
        "source": "backend/parser/ast_parser_10.py",
        "target": "backend/parser/ast_parser_11.py"
    },
    {
        "source": "backend/graph/graph_engine_19.py",
        "target": "backend/graph/graph_engine_14.py"
    },
    {
        "source": "backend/parser/ast_parser_41.py",
        "target": "backend/parser/ast_parser_42.py"
    },
    {
        "source": "frontend/components/ui/component_29.tsx",
        "target": "frontend/components/ui/component_20.tsx"
    },
    {
        "source": "backend/rag/vector_service_13.py",
        "target": "backend/rag/vector_service_06.py"
    },
    {
        "source": "backend/rag/vector_service_04.py",
        "target": "backend/rag/vector_service_05.py"
    },
    {
        "source": "backend/rag/vector_service_01.py",
        "target": "backend/rag/vector_service_02.py"
    },
    {
        "source": "backend/database/model_17.py",
        "target": "backend/rag/vector_service_44.py"
    },
    {
        "source": "backend/security/scanner_10.py",
        "target": "backend/security/scanner_11.py"
    },
    {
        "source": "backend/parser/ast_parser_26.py",
        "target": "backend/api/route_18.py"
    },
    {
        "source": "backend/parser/ast_parser_15.py",
        "target": "backend/parser/ast_parser_13.py"
    },
    {
        "source": "backend/api/route_01.py",
        "target": "backend/api/route_02.py"
    },
    {
        "source": "backend/security/scanner_18.py",
        "target": "backend/security/scanner_19.py"
    },
    {
        "source": "backend/graph/graph_engine_24.py",
        "target": "backend/api/route_09.py"
    },
    {
        "source": "backend/graph/graph_engine_10.py",
        "target": "backend/graph/graph_engine_02.py"
    },
    {
        "source": "backend/parser/ast_parser_28.py",
        "target": "backend/parser/ast_parser_05.py"
    },
    {
        "source": "backend/parser/ast_parser_22.py",
        "target": "backend/parser/ast_parser_23.py"
    },
    {
        "source": "backend/api/route_15.py",
        "target": "backend/api/route_09.py"
    },
    {
        "source": "backend/rag/vector_service_39.py",
        "target": "backend/rag/vector_service_19.py"
    },
    {
        "source": "backend/parser/ast_parser_05.py",
        "target": "backend/parser/ast_parser_06.py"
    },
    {
        "source": "backend/database/model_35.py",
        "target": "backend/database/model_04.py"
    },
    {
        "source": "backend/parser/ast_parser_40.py",
        "target": "backend/parser/ast_parser_41.py"
    },
    {
        "source": "backend/parser/ast_parser_25.py",
        "target": "backend/rag/vector_service_41.py"
    },
    {
        "source": "frontend/components/ui/component_37.tsx",
        "target": "frontend/components/ui/component_38.tsx"
    },
    {
        "source": "backend/rag/vector_service_36.py",
        "target": "backend/rag/vector_service_22.py"
    },
    {
        "source": "backend/database/model_27.py",
        "target": "frontend/components/ui/component_34.tsx"
    },
    {
        "source": "backend/security/scanner_16.py",
        "target": "backend/security/scanner_02.py"
    },
    {
        "source": "backend/database/model_27.py",
        "target": "backend/database/model_13.py"
    },
    {
        "source": "backend/rag/vector_service_05.py",
        "target": "backend/rag/vector_service_06.py"
    },
    {
        "source": "backend/api/route_23.py",
        "target": "backend/api/route_24.py"
    },
    {
        "source": "backend/rag/vector_service_24.py",
        "target": "backend/rag/vector_service_31.py"
    },
    {
        "source": "backend/parser/ast_parser_01.py",
        "target": "backend/parser/ast_parser_43.py"
    },
    {
        "source": "backend/rag/vector_service_41.py",
        "target": "backend/rag/vector_service_42.py"
    },
    {
        "source": "frontend/components/ui/component_49.tsx",
        "target": "frontend/components/ui/component_36.tsx"
    },
    {
        "source": "backend/rag/vector_service_43.py",
        "target": "backend/parser/ast_parser_08.py"
    },
    {
        "source": "backend/graph/graph_engine_11.py",
        "target": "backend/graph/graph_engine_12.py"
    },
    {
        "source": "backend/rag/vector_service_04.py",
        "target": "backend/rag/vector_service_36.py"
    },
    {
        "source": "backend/database/model_28.py",
        "target": "backend/database/model_27.py"
    },
    {
        "source": "backend/api/route_11.py",
        "target": "backend/api/route_12.py"
    },
    {
        "source": "backend/database/model_34.py",
        "target": "backend/database/model_39.py"
    },
    {
        "source": "frontend/components/ui/component_24.tsx",
        "target": "frontend/components/ui/component_40.tsx"
    },
    {
        "source": "backend/parser/ast_parser_27.py",
        "target": "backend/parser/ast_parser_02.py"
    },
    {
        "source": "backend/graph/graph_engine_37.py",
        "target": "backend/graph/graph_engine_38.py"
    },
    {
        "source": "backend/graph/graph_engine_23.py",
        "target": "backend/graph/graph_engine_20.py"
    },
    {
        "source": "frontend/components/ui/component_44.tsx",
        "target": "frontend/components/ui/component_18.tsx"
    },
    {
        "source": "frontend/components/ui/component_32.tsx",
        "target": "backend/database/model_38.py"
    },
    {
        "source": "backend/database/model_16.py",
        "target": "backend/database/model_26.py"
    },
    {
        "source": "frontend/components/ui/component_08.tsx",
        "target": "frontend/components/ui/component_50.tsx"
    },
    {
        "source": "backend/graph/graph_engine_09.py",
        "target": "backend/graph/graph_engine_10.py"
    },
    {
        "source": "backend/rag/vector_service_39.py",
        "target": "backend/rag/vector_service_45.py"
    },
    {
        "source": "backend/graph/graph_engine_02.py",
        "target": "backend/graph/graph_engine_06.py"
    },
    {
        "source": "backend/security/scanner_11.py",
        "target": "backend/security/scanner_13.py"
    },
    {
        "source": "backend/api/route_30.py",
        "target": "backend/api/route_35.py"
    },
    {
        "source": "backend/parser/ast_parser_23.py",
        "target": "backend/parser/ast_parser_14.py"
    },
    {
        "source": "backend/parser/ast_parser_43.py",
        "target": "backend/parser/ast_parser_25.py"
    },
    {
        "source": "backend/graph/graph_engine_43.py",
        "target": "backend/parser/ast_parser_01.py"
    },
    {
        "source": "backend/parser/ast_parser_05.py",
        "target": "backend/parser/ast_parser_16.py"
    },
    {
        "source": "utils/helpers/standalone_util_18.py",
        "target": "utils/helpers/standalone_util_19.py"
    },
    {
        "source": "utils/helpers/standalone_util_23.py",
        "target": "utils/helpers/standalone_util_24.py"
    },
    {
        "source": "backend/database/model_44.py",
        "target": "backend/database/model_45.py"
    },
    {
        "source": "frontend/components/ui/component_29.tsx",
        "target": "frontend/components/ui/component_45.tsx"
    },
    {
        "source": "backend/database/model_39.py",
        "target": "backend/database/model_03.py"
    },
    {
        "source": "backend/parser/ast_parser_33.py",
        "target": "backend/parser/ast_parser_20.py"
    },
    {
        "source": "backend/graph/graph_engine_43.py",
        "target": "backend/graph/graph_engine_41.py"
    },
    {
        "source": "backend/parser/ast_parser_36.py",
        "target": "backend/parser/ast_parser_37.py"
    },
    {
        "source": "backend/rag/vector_service_21.py",
        "target": "backend/rag/vector_service_16.py"
    },
    {
        "source": "frontend/components/ui/component_26.tsx",
        "target": "frontend/components/ui/component_18.tsx"
    },
    {
        "source": "backend/security/scanner_11.py",
        "target": "backend/security/scanner_12.py"
    },
    {
        "source": "utils/helpers/standalone_util_12.py",
        "target": "utils/helpers/standalone_util_13.py"
    },
    {
        "source": "utils/helpers/standalone_util_22.py",
        "target": "utils/helpers/standalone_util_23.py"
    },
    {
        "source": "backend/api/route_39.py",
        "target": "backend/api/route_11.py"
    },
    {
        "source": "backend/graph/graph_engine_26.py",
        "target": "backend/graph/graph_engine_38.py"
    },
    {
        "source": "backend/graph/graph_engine_26.py",
        "target": "backend/graph/graph_engine_27.py"
    },
    {
        "source": "backend/security/scanner_15.py",
        "target": "backend/security/scanner_01.py"
    },
    {
        "source": "backend/graph/graph_engine_06.py",
        "target": "backend/graph/graph_engine_09.py"
    },
    {
        "source": "backend/graph/graph_engine_37.py",
        "target": "backend/graph/graph_engine_43.py"
    },
    {
        "source": "backend/parser/ast_parser_44.py",
        "target": "backend/parser/ast_parser_45.py"
    },
    {
        "source": "backend/database/model_20.py",
        "target": "backend/database/model_30.py"
    },
    {
        "source": "frontend/components/ui/component_33.tsx",
        "target": "frontend/components/ui/component_35.tsx"
    },
    {
        "source": "backend/rag/vector_service_32.py",
        "target": "backend/rag/vector_service_14.py"
    },
    {
        "source": "frontend/components/ui/component_30.tsx",
        "target": "frontend/components/ui/component_45.tsx"
    },
    {
        "source": "backend/api/route_30.py",
        "target": "backend/api/route_31.py"
    },
    {
        "source": "frontend/components/ui/component_28.tsx",
        "target": "backend/api/route_07.py"
    },
    {
        "source": "backend/rag/vector_service_42.py",
        "target": "backend/rag/vector_service_03.py"
    },
    {
        "source": "backend/parser/ast_parser_03.py",
        "target": "backend/parser/ast_parser_46.py"
    },
    {
        "source": "backend/parser/ast_parser_33.py",
        "target": "backend/parser/ast_parser_34.py"
    },
    {
        "source": "backend/api/route_18.py",
        "target": "backend/api/route_05.py"
    },
    {
        "source": "backend/rag/vector_service_24.py",
        "target": "backend/rag/vector_service_12.py"
    },
    {
        "source": "backend/parser/ast_parser_07.py",
        "target": "backend/parser/ast_parser_08.py"
    },
    {
        "source": "backend/parser/ast_parser_06.py",
        "target": "backend/parser/ast_parser_07.py"
    },
    {
        "source": "backend/rag/vector_service_35.py",
        "target": "backend/rag/vector_service_36.py"
    },
    {
        "source": "backend/api/route_21.py",
        "target": "backend/api/route_04.py"
    },
    {
        "source": "backend/rag/vector_service_30.py",
        "target": "backend/rag/vector_service_18.py"
    },
    {
        "source": "backend/database/model_27.py",
        "target": "backend/database/model_43.py"
    },
    {
        "source": "backend/api/route_27.py",
        "target": "backend/api/route_28.py"
    },
    {
        "source": "backend/database/model_13.py",
        "target": "backend/database/model_14.py"
    },
    {
        "source": "backend/api/route_18.py",
        "target": "backend/rag/vector_service_02.py"
    },
    {
        "source": "backend/graph/graph_engine_28.py",
        "target": "frontend/components/ui/component_32.tsx"
    },
    {
        "source": "backend/rag/vector_service_27.py",
        "target": "backend/graph/graph_engine_18.py"
    },
    {
        "source": "backend/api/route_31.py",
        "target": "backend/api/route_32.py"
    },
    {
        "source": "backend/api/route_33.py",
        "target": "backend/api/route_34.py"
    },
    {
        "source": "backend/rag/vector_service_28.py",
        "target": "backend/rag/vector_service_29.py"
    },
    {
        "source": "backend/security/scanner_01.py",
        "target": "backend/rag/vector_service_18.py"
    },
    {
        "source": "backend/graph/graph_engine_36.py",
        "target": "backend/graph/graph_engine_37.py"
    },
    {
        "source": "backend/database/model_35.py",
        "target": "backend/database/model_36.py"
    },
    {
        "source": "backend/parser/ast_parser_20.py",
        "target": "backend/parser/ast_parser_15.py"
    },
    {
        "source": "backend/graph/graph_engine_26.py",
        "target": "backend/graph/graph_engine_36.py"
    },
    {
        "source": "backend/database/model_03.py",
        "target": "backend/api/route_20.py"
    },
    {
        "source": "backend/database/model_25.py",
        "target": "backend/database/model_26.py"
    },
    {
        "source": "frontend/components/ui/component_37.tsx",
        "target": "frontend/components/ui/component_41.tsx"
    },
    {
        "source": "backend/parser/ast_parser_41.py",
        "target": "backend/parser/ast_parser_17.py"
    },
    {
        "source": "backend/graph/graph_engine_07.py",
        "target": "backend/security/scanner_11.py"
    },
    {
        "source": "backend/database/model_17.py",
        "target": "backend/database/model_18.py"
    },
    {
        "source": "frontend/components/ui/component_31.tsx",
        "target": "frontend/components/ui/component_08.tsx"
    },
    {
        "source": "backend/parser/ast_parser_20.py",
        "target": "backend/rag/vector_service_41.py"
    },
    {
        "source": "backend/api/route_21.py",
        "target": "backend/api/route_26.py"
    },
    {
        "source": "backend/parser/ast_parser_19.py",
        "target": "frontend/components/ui/component_02.tsx"
    },
    {
        "source": "backend/rag/vector_service_14.py",
        "target": "backend/security/scanner_05.py"
    },
    {
        "source": "backend/graph/graph_engine_18.py",
        "target": "backend/graph/graph_engine_34.py"
    },
    {
        "source": "backend/graph/graph_engine_40.py",
        "target": "backend/api/route_36.py"
    },
    {
        "source": "backend/api/route_22.py",
        "target": "backend/api/route_07.py"
    },
    {
        "source": "backend/database/model_31.py",
        "target": "backend/database/model_33.py"
    },
    {
        "source": "backend/database/model_29.py",
        "target": "backend/database/model_34.py"
    },
    {
        "source": "backend/security/scanner_16.py",
        "target": "backend/security/scanner_12.py"
    },
    {
        "source": "backend/graph/graph_engine_43.py",
        "target": "backend/graph/graph_engine_44.py"
    },
    {
        "source": "backend/rag/vector_service_03.py",
        "target": "backend/rag/vector_service_04.py"
    },
    {
        "source": "backend/rag/vector_service_42.py",
        "target": "backend/rag/vector_service_43.py"
    },
    {
        "source": "backend/api/route_30.py",
        "target": "backend/api/route_34.py"
    },
    {
        "source": "backend/parser/ast_parser_11.py",
        "target": "backend/parser/ast_parser_12.py"
    },
    {
        "source": "backend/parser/ast_parser_48.py",
        "target": "frontend/components/ui/component_45.tsx"
    },
    {
        "source": "backend/graph/graph_engine_06.py",
        "target": "backend/graph/graph_engine_16.py"
    },
    {
        "source": "backend/database/model_45.py",
        "target": "backend/parser/ast_parser_49.py"
    },
    {
        "source": "frontend/components/ui/component_15.tsx",
        "target": "frontend/components/ui/component_19.tsx"
    },
    {
        "source": "backend/database/model_29.py",
        "target": "backend/database/model_30.py"
    },
    {
        "source": "backend/graph/graph_engine_31.py",
        "target": "backend/graph/graph_engine_32.py"
    },
    {
        "source": "frontend/components/ui/component_22.tsx",
        "target": "frontend/components/ui/component_21.tsx"
    },
    {
        "source": "backend/rag/vector_service_13.py",
        "target": "backend/rag/vector_service_05.py"
    },
    {
        "source": "backend/api/route_15.py",
        "target": "backend/api/route_16.py"
    },
    {
        "source": "backend/rag/vector_service_23.py",
        "target": "backend/rag/vector_service_28.py"
    },
    {
        "source": "backend/api/route_08.py",
        "target": "backend/api/route_24.py"
    },
    {
        "source": "backend/api/route_22.py",
        "target": "backend/api/route_18.py"
    },
    {
        "source": "backend/api/route_13.py",
        "target": "backend/api/route_14.py"
    },
    {
        "source": "backend/database/model_21.py",
        "target": "backend/database/model_05.py"
    },
    {
        "source": "backend/parser/ast_parser_37.py",
        "target": "backend/parser/ast_parser_20.py"
    },
    {
        "source": "frontend/components/ui/component_28.tsx",
        "target": "frontend/components/ui/component_08.tsx"
    },
    {
        "source": "backend/api/route_23.py",
        "target": "backend/api/route_14.py"
    },
    {
        "source": "backend/graph/graph_engine_01.py",
        "target": "backend/graph/graph_engine_20.py"
    },
    {
        "source": "backend/api/route_36.py",
        "target": "frontend/components/ui/component_47.tsx"
    },
    {
        "source": "backend/database/model_22.py",
        "target": "backend/graph/graph_engine_30.py"
    },
    {
        "source": "frontend/components/ui/component_47.tsx",
        "target": "frontend/components/ui/component_48.tsx"
    },
    {
        "source": "backend/rag/vector_service_01.py",
        "target": "backend/rag/vector_service_34.py"
    },
    {
        "source": "backend/graph/graph_engine_24.py",
        "target": "backend/graph/graph_engine_25.py"
    },
    {
        "source": "backend/graph/graph_engine_33.py",
        "target": "backend/graph/graph_engine_34.py"
    },
    {
        "source": "backend/graph/graph_engine_44.py",
        "target": "backend/graph/graph_engine_26.py"
    },
    {
        "source": "backend/rag/vector_service_09.py",
        "target": "backend/rag/vector_service_10.py"
    },
    {
        "source": "backend/parser/ast_parser_50.py",
        "target": "backend/parser/ast_parser_09.py"
    },
    {
        "source": "backend/database/model_34.py",
        "target": "backend/database/model_21.py"
    },
    {
        "source": "backend/parser/ast_parser_32.py",
        "target": "backend/parser/ast_parser_33.py"
    },
    {
        "source": "backend/parser/ast_parser_07.py",
        "target": "backend/parser/ast_parser_25.py"
    },
    {
        "source": "backend/database/model_43.py",
        "target": "backend/database/model_44.py"
    },
    {
        "source": "backend/api/route_01.py",
        "target": "backend/api/route_17.py"
    },
    {
        "source": "backend/graph/graph_engine_14.py",
        "target": "backend/graph/graph_engine_33.py"
    },
    {
        "source": "backend/graph/graph_engine_29.py",
        "target": "backend/graph/graph_engine_44.py"
    },
    {
        "source": "backend/rag/vector_service_23.py",
        "target": "backend/rag/vector_service_24.py"
    },
    {
        "source": "frontend/components/ui/component_01.tsx",
        "target": "frontend/components/ui/component_27.tsx"
    },
    {
        "source": "backend/database/model_05.py",
        "target": "backend/database/model_22.py"
    },
    {
        "source": "frontend/components/ui/component_02.tsx",
        "target": "frontend/components/ui/component_03.tsx"
    },
    {
        "source": "backend/database/model_23.py",
        "target": "backend/database/model_24.py"
    },
    {
        "source": "backend/graph/graph_engine_30.py",
        "target": "backend/graph/graph_engine_09.py"
    },
    {
        "source": "backend/rag/vector_service_34.py",
        "target": "backend/rag/vector_service_35.py"
    },
    {
        "source": "backend/rag/vector_service_11.py",
        "target": "backend/rag/vector_service_20.py"
    },
    {
        "source": "backend/security/scanner_17.py",
        "target": "backend/security/scanner_09.py"
    },
    {
        "source": "backend/parser/ast_parser_28.py",
        "target": "backend/parser/ast_parser_23.py"
    },
    {
        "source": "frontend/components/ui/component_15.tsx",
        "target": "frontend/components/ui/component_44.tsx"
    },
    {
        "source": "backend/parser/ast_parser_13.py",
        "target": "backend/parser/ast_parser_14.py"
    },
    {
        "source": "backend/rag/vector_service_40.py",
        "target": "backend/rag/vector_service_43.py"
    },
    {
        "source": "backend/rag/vector_service_24.py",
        "target": "backend/rag/vector_service_41.py"
    },
    {
        "source": "backend/parser/ast_parser_17.py",
        "target": "backend/parser/ast_parser_33.py"
    },
    {
        "source": "backend/graph/graph_engine_35.py",
        "target": "backend/graph/graph_engine_02.py"
    },
    {
        "source": "backend/database/model_16.py",
        "target": "backend/database/model_38.py"
    },
    {
        "source": "backend/graph/graph_engine_29.py",
        "target": "backend/graph/graph_engine_30.py"
    },
    {
        "source": "backend/rag/vector_service_02.py",
        "target": "backend/rag/vector_service_03.py"
    },
    {
        "source": "frontend/components/ui/component_41.tsx",
        "target": "frontend/components/ui/component_32.tsx"
    },
    {
        "source": "backend/api/route_38.py",
        "target": "backend/api/route_26.py"
    },
    {
        "source": "backend/api/route_39.py",
        "target": "backend/api/route_21.py"
    },
    {
        "source": "frontend/components/ui/component_05.tsx",
        "target": "frontend/components/ui/component_26.tsx"
    },
    {
        "source": "backend/rag/vector_service_13.py",
        "target": "backend/rag/vector_service_02.py"
    },
    {
        "source": "backend/parser/ast_parser_46.py",
        "target": "backend/parser/ast_parser_28.py"
    },
    {
        "source": "backend/rag/vector_service_07.py",
        "target": "backend/rag/vector_service_45.py"
    },
    {
        "source": "backend/parser/ast_parser_38.py",
        "target": "backend/parser/ast_parser_39.py"
    },
    {
        "source": "backend/rag/vector_service_35.py",
        "target": "backend/rag/vector_service_31.py"
    },
    {
        "source": "frontend/components/ui/component_36.tsx",
        "target": "frontend/components/ui/component_09.tsx"
    },
    {
        "source": "frontend/components/ui/component_33.tsx",
        "target": "frontend/components/ui/component_34.tsx"
    },
    {
        "source": "backend/graph/graph_engine_35.py",
        "target": "backend/graph/graph_engine_04.py"
    },
    {
        "source": "backend/parser/ast_parser_15.py",
        "target": "backend/parser/ast_parser_02.py"
    },
    {
        "source": "backend/parser/ast_parser_04.py",
        "target": "backend/parser/ast_parser_05.py"
    },
    {
        "source": "backend/graph/graph_engine_11.py",
        "target": "backend/graph/graph_engine_31.py"
    },
    {
        "source": "backend/parser/ast_parser_14.py",
        "target": "backend/parser/ast_parser_46.py"
    },
    {
        "source": "backend/rag/vector_service_35.py",
        "target": "backend/rag/vector_service_09.py"
    },
    {
        "source": "backend/parser/ast_parser_27.py",
        "target": "backend/parser/ast_parser_28.py"
    },
    {
        "source": "backend/database/model_16.py",
        "target": "backend/database/model_18.py"
    },
    {
        "source": "backend/graph/graph_engine_16.py",
        "target": "backend/graph/graph_engine_08.py"
    },
    {
        "source": "backend/api/route_36.py",
        "target": "backend/api/route_37.py"
    },
    {
        "source": "backend/database/model_09.py",
        "target": "backend/database/model_10.py"
    },
    {
        "source": "backend/rag/vector_service_19.py",
        "target": "backend/rag/vector_service_15.py"
    },
    {
        "source": "frontend/components/ui/component_16.tsx",
        "target": "frontend/components/ui/component_08.tsx"
    },
    {
        "source": "backend/parser/ast_parser_19.py",
        "target": "backend/parser/ast_parser_20.py"
    },
    {
        "source": "frontend/components/ui/component_41.tsx",
        "target": "frontend/components/ui/component_29.tsx"
    },
    {
        "source": "backend/database/model_26.py",
        "target": "backend/database/model_09.py"
    },
    {
        "source": "backend/parser/ast_parser_25.py",
        "target": "backend/parser/ast_parser_26.py"
    },
    {
        "source": "backend/graph/graph_engine_27.py",
        "target": "backend/graph/graph_engine_22.py"
    },
    {
        "source": "backend/parser/ast_parser_29.py",
        "target": "backend/parser/ast_parser_30.py"
    },
    {
        "source": "backend/parser/ast_parser_16.py",
        "target": "backend/parser/ast_parser_18.py"
    },
    {
        "source": "backend/rag/vector_service_22.py",
        "target": "backend/rag/vector_service_01.py"
    },
    {
        "source": "backend/parser/ast_parser_43.py",
        "target": "backend/parser/ast_parser_22.py"
    },
    {
        "source": "backend/security/scanner_09.py",
        "target": "backend/security/scanner_14.py"
    },
    {
        "source": "backend/rag/vector_service_15.py",
        "target": "backend/rag/vector_service_16.py"
    },
    {
        "source": "backend/api/route_32.py",
        "target": "backend/api/route_26.py"
    },
    {
        "source": "backend/api/route_06.py",
        "target": "backend/api/route_36.py"
    },
    {
        "source": "backend/parser/ast_parser_43.py",
        "target": "backend/parser/ast_parser_48.py"
    },
    {
        "source": "backend/parser/ast_parser_43.py",
        "target": "backend/parser/ast_parser_44.py"
    },
    {
        "source": "backend/parser/ast_parser_33.py",
        "target": "backend/parser/ast_parser_08.py"
    },
    {
        "source": "backend/rag/vector_service_20.py",
        "target": "backend/rag/vector_service_44.py"
    },
    {
        "source": "backend/graph/graph_engine_37.py",
        "target": "backend/graph/graph_engine_25.py"
    },
    {
        "source": "frontend/components/ui/component_42.tsx",
        "target": "backend/database/model_41.py"
    },
    {
        "source": "backend/parser/ast_parser_46.py",
        "target": "backend/parser/ast_parser_47.py"
    },
    {
        "source": "backend/parser/ast_parser_09.py",
        "target": "frontend/components/ui/component_06.tsx"
    },
    {
        "source": "backend/parser/ast_parser_20.py",
        "target": "backend/parser/ast_parser_40.py"
    },
    {
        "source": "backend/graph/graph_engine_39.py",
        "target": "backend/graph/graph_engine_40.py"
    },
    {
        "source": "backend/graph/graph_engine_24.py",
        "target": "backend/database/model_07.py"
    },
    {
        "source": "backend/graph/graph_engine_16.py",
        "target": "backend/graph/graph_engine_41.py"
    },
    {
        "source": "backend/graph/graph_engine_45.py",
        "target": "backend/graph/graph_engine_25.py"
    },
    {
        "source": "backend/database/model_32.py",
        "target": "backend/database/model_33.py"
    },
    {
        "source": "backend/rag/vector_service_43.py",
        "target": "backend/rag/vector_service_44.py"
    },
    {
        "source": "backend/database/model_04.py",
        "target": "backend/database/model_16.py"
    },
    {
        "source": "backend/rag/vector_service_26.py",
        "target": "backend/rag/vector_service_27.py"
    },
    {
        "source": "backend/parser/ast_parser_45.py",
        "target": "backend/parser/ast_parser_46.py"
    },
    {
        "source": "backend/rag/vector_service_16.py",
        "target": "backend/rag/vector_service_45.py"
    },
    {
        "source": "backend/security/scanner_16.py",
        "target": "backend/security/scanner_09.py"
    },
    {
        "source": "backend/parser/ast_parser_35.py",
        "target": "backend/parser/ast_parser_46.py"
    },
    {
        "source": "backend/rag/vector_service_07.py",
        "target": "backend/graph/graph_engine_45.py"
    },
    {
        "source": "backend/security/scanner_09.py",
        "target": "backend/database/model_31.py"
    },
    {
        "source": "backend/rag/vector_service_30.py",
        "target": "backend/rag/vector_service_31.py"
    },
    {
        "source": "backend/parser/ast_parser_03.py",
        "target": "backend/parser/ast_parser_04.py"
    },
    {
        "source": "backend/parser/ast_parser_31.py",
        "target": "backend/parser/ast_parser_32.py"
    },
    {
        "source": "frontend/components/ui/component_41.tsx",
        "target": "frontend/components/ui/component_39.tsx"
    },
    {
        "source": "backend/parser/ast_parser_36.py",
        "target": "backend/parser/ast_parser_09.py"
    },
    {
        "source": "backend/graph/graph_engine_30.py",
        "target": "backend/graph/graph_engine_43.py"
    },
    {
        "source": "backend/api/route_25.py",
        "target": "backend/api/route_18.py"
    },
    {
        "source": "backend/rag/vector_service_11.py",
        "target": "backend/rag/vector_service_12.py"
    },
    {
        "source": "backend/api/route_06.py",
        "target": "backend/api/route_07.py"
    },
    {
        "source": "backend/graph/graph_engine_27.py",
        "target": "backend/graph/graph_engine_28.py"
    },
    {
        "source": "backend/parser/ast_parser_22.py",
        "target": "backend/parser/ast_parser_02.py"
    },
    {
        "source": "frontend/components/ui/component_06.tsx",
        "target": "frontend/components/ui/component_31.tsx"
    },
    {
        "source": "backend/graph/graph_engine_07.py",
        "target": "backend/api/route_16.py"
    },
    {
        "source": "backend/graph/graph_engine_28.py",
        "target": "backend/graph/graph_engine_15.py"
    },
    {
        "source": "backend/parser/ast_parser_07.py",
        "target": "backend/parser/ast_parser_39.py"
    },
    {
        "source": "backend/database/model_42.py",
        "target": "backend/database/model_35.py"
    },
    {
        "source": "backend/api/route_29.py",
        "target": "backend/api/route_38.py"
    },
    {
        "source": "backend/database/model_21.py",
        "target": "backend/database/model_04.py"
    },
    {
        "source": "backend/rag/vector_service_21.py",
        "target": "backend/rag/vector_service_12.py"
    },
    {
        "source": "frontend/components/ui/component_31.tsx",
        "target": "frontend/components/ui/component_29.tsx"
    },
    {
        "source": "frontend/components/ui/component_35.tsx",
        "target": "frontend/components/ui/component_36.tsx"
    },
    {
        "source": "backend/database/model_13.py",
        "target": "backend/database/model_35.py"
    },
    {
        "source": "backend/graph/graph_engine_21.py",
        "target": "backend/graph/graph_engine_14.py"
    },
    {
        "source": "frontend/components/ui/component_28.tsx",
        "target": "frontend/components/ui/component_29.tsx"
    },
    {
        "source": "frontend/components/ui/component_20.tsx",
        "target": "frontend/components/ui/component_06.tsx"
    },
    {
        "source": "backend/graph/graph_engine_19.py",
        "target": "backend/api/route_38.py"
    },
    {
        "source": "backend/parser/ast_parser_04.py",
        "target": "backend/parser/ast_parser_06.py"
    },
    {
        "source": "backend/graph/graph_engine_28.py",
        "target": "backend/graph/graph_engine_38.py"
    },
    {
        "source": "backend/parser/ast_parser_43.py",
        "target": "backend/parser/ast_parser_27.py"
    },
    {
        "source": "backend/graph/graph_engine_12.py",
        "target": "backend/graph/graph_engine_45.py"
    },
    {
        "source": "backend/database/model_01.py",
        "target": "backend/database/model_05.py"
    },
    {
        "source": "backend/rag/vector_service_30.py",
        "target": "backend/rag/vector_service_28.py"
    },
    {
        "source": "backend/api/route_11.py",
        "target": "backend/api/route_24.py"
    },
    {
        "source": "backend/parser/ast_parser_49.py",
        "target": "backend/parser/ast_parser_50.py"
    },
    {
        "source": "backend/parser/ast_parser_43.py",
        "target": "backend/parser/ast_parser_07.py"
    },
    {
        "source": "backend/graph/graph_engine_40.py",
        "target": "backend/graph/graph_engine_22.py"
    },
    {
        "source": "backend/database/model_05.py",
        "target": "backend/database/model_39.py"
    },
    {
        "source": "backend/rag/vector_service_10.py",
        "target": "backend/rag/vector_service_11.py"
    },
    {
        "source": "backend/parser/ast_parser_10.py",
        "target": "backend/parser/ast_parser_18.py"
    },
    {
        "source": "backend/graph/graph_engine_09.py",
        "target": "backend/graph/graph_engine_30.py"
    },
    {
        "source": "backend/database/model_16.py",
        "target": "backend/database/model_15.py"
    },
    {
        "source": "frontend/components/ui/component_14.tsx",
        "target": "backend/rag/vector_service_25.py"
    },
    {
        "source": "backend/security/scanner_16.py",
        "target": "backend/security/scanner_05.py"
    },
    {
        "source": "backend/security/scanner_18.py",
        "target": "backend/graph/graph_engine_40.py"
    },
    {
        "source": "backend/graph/graph_engine_23.py",
        "target": "backend/rag/vector_service_37.py"
    },
    {
        "source": "frontend/components/ui/component_10.tsx",
        "target": "frontend/components/ui/component_11.tsx"
    },
    {
        "source": "backend/database/model_40.py",
        "target": "backend/database/model_41.py"
    },
    {
        "source": "frontend/components/ui/component_15.tsx",
        "target": "backend/graph/graph_engine_07.py"
    },
    {
        "source": "utils/helpers/standalone_util_02.py",
        "target": "utils/helpers/standalone_util_03.py"
    },
    {
        "source": "backend/rag/vector_service_37.py",
        "target": "backend/rag/vector_service_44.py"
    },
    {
        "source": "backend/rag/vector_service_08.py",
        "target": "backend/rag/vector_service_35.py"
    },
    {
        "source": "utils/helpers/standalone_util_06.py",
        "target": "utils/helpers/standalone_util_07.py"
    },
    {
        "source": "frontend/components/ui/component_48.tsx",
        "target": "frontend/components/ui/component_49.tsx"
    },
    {
        "source": "backend/database/model_19.py",
        "target": "backend/database/model_20.py"
    },
    {
        "source": "backend/database/model_27.py",
        "target": "backend/database/model_28.py"
    },
    {
        "source": "backend/graph/graph_engine_03.py",
        "target": "backend/graph/graph_engine_16.py"
    },
    {
        "source": "backend/rag/vector_service_18.py",
        "target": "backend/rag/vector_service_03.py"
    },
    {
        "source": "backend/parser/ast_parser_03.py",
        "target": "backend/parser/ast_parser_31.py"
    },
    {
        "source": "frontend/components/ui/component_32.tsx",
        "target": "frontend/components/ui/component_19.tsx"
    },
    {
        "source": "backend/database/model_05.py",
        "target": "backend/database/model_33.py"
    },
    {
        "source": "backend/api/route_27.py",
        "target": "backend/api/route_15.py"
    },
    {
        "source": "backend/graph/graph_engine_06.py",
        "target": "backend/graph/graph_engine_07.py"
    },
    {
        "source": "frontend/components/ui/component_27.tsx",
        "target": "frontend/components/ui/component_45.tsx"
    },
    {
        "source": "backend/api/route_20.py",
        "target": "backend/api/route_33.py"
    },
    {
        "source": "backend/api/route_36.py",
        "target": "backend/api/route_15.py"
    },
    {
        "source": "backend/graph/graph_engine_39.py",
        "target": "backend/graph/graph_engine_42.py"
    },
    {
        "source": "backend/parser/ast_parser_36.py",
        "target": "backend/parser/ast_parser_27.py"
    },
    {
        "source": "frontend/components/ui/component_36.tsx",
        "target": "frontend/components/ui/component_37.tsx"
    },
    {
        "source": "backend/api/route_06.py",
        "target": "backend/api/route_38.py"
    },
    {
        "source": "backend/parser/ast_parser_30.py",
        "target": "backend/parser/ast_parser_23.py"
    },
    {
        "source": "backend/security/scanner_19.py",
        "target": "backend/security/scanner_20.py"
    },
    {
        "source": "backend/graph/graph_engine_28.py",
        "target": "backend/graph/graph_engine_32.py"
    },
    {
        "source": "backend/rag/vector_service_39.py",
        "target": "backend/rag/vector_service_08.py"
    },
    {
        "source": "backend/graph/graph_engine_23.py",
        "target": "backend/graph/graph_engine_24.py"
    },
    {
        "source": "backend/database/model_03.py",
        "target": "backend/database/model_22.py"
    },
    {
        "source": "backend/graph/graph_engine_37.py",
        "target": "backend/graph/graph_engine_13.py"
    },
    {
        "source": "backend/security/scanner_17.py",
        "target": "backend/security/scanner_18.py"
    },
    {
        "source": "backend/api/route_18.py",
        "target": "backend/api/route_01.py"
    },
    {
        "source": "backend/api/route_35.py",
        "target": "backend/api/route_18.py"
    },
    {
        "source": "backend/database/model_04.py",
        "target": "backend/database/model_26.py"
    },
    {
        "source": "frontend/components/ui/component_07.tsx",
        "target": "frontend/components/ui/component_49.tsx"
    },
    {
        "source": "backend/database/model_15.py",
        "target": "backend/database/model_16.py"
    },
    {
        "source": "backend/security/scanner_13.py",
        "target": "backend/security/scanner_05.py"
    },
    {
        "source": "frontend/components/ui/component_11.tsx",
        "target": "frontend/components/ui/component_12.tsx"
    },
    {
        "source": "backend/parser/ast_parser_08.py",
        "target": "backend/rag/vector_service_30.py"
    },
    {
        "source": "backend/database/model_04.py",
        "target": "backend/database/model_33.py"
    },
    {
        "source": "backend/api/route_22.py",
        "target": "backend/api/route_08.py"
    },
    {
        "source": "backend/graph/graph_engine_11.py",
        "target": "backend/graph/graph_engine_30.py"
    },
    {
        "source": "backend/security/scanner_07.py",
        "target": "backend/security/scanner_17.py"
    },
    {
        "source": "backend/rag/vector_service_15.py",
        "target": "backend/parser/ast_parser_41.py"
    },
    {
        "source": "backend/api/route_19.py",
        "target": "backend/database/model_15.py"
    },
    {
        "source": "backend/graph/graph_engine_17.py",
        "target": "backend/graph/graph_engine_25.py"
    },
    {
        "source": "frontend/components/ui/component_18.tsx",
        "target": "frontend/components/ui/component_19.tsx"
    },
    {
        "source": "frontend/components/ui/component_15.tsx",
        "target": "frontend/components/ui/component_50.tsx"
    },
    {
        "source": "backend/database/model_41.py",
        "target": "backend/database/model_42.py"
    },
    {
        "source": "backend/graph/graph_engine_25.py",
        "target": "backend/graph/graph_engine_38.py"
    },
    {
        "source": "backend/api/route_07.py",
        "target": "backend/api/route_08.py"
    },
    {
        "source": "backend/rag/vector_service_23.py",
        "target": "backend/parser/ast_parser_07.py"
    },
    {
        "source": "backend/security/scanner_04.py",
        "target": "frontend/components/ui/component_29.tsx"
    },
    {
        "source": "backend/api/route_33.py",
        "target": "backend/graph/graph_engine_15.py"
    },
    {
        "source": "utils/helpers/standalone_util_07.py",
        "target": "utils/helpers/standalone_util_08.py"
    },
    {
        "source": "frontend/components/ui/component_03.tsx",
        "target": "frontend/components/ui/component_28.tsx"
    },
    {
        "source": "utils/helpers/standalone_util_13.py",
        "target": "backend/parser/ast_parser_01.py"
    },
    {
        "source": "backend/graph/graph_engine_22.py",
        "target": "backend/graph/graph_engine_43.py"
    },
    {
        "source": "backend/rag/vector_service_26.py",
        "target": "backend/rag/vector_service_45.py"
    }
],
};

const MOCK_NOTIFICATIONS: NotificationItem[] = [
  {
    id: "notif-01",
    type: "risk_alert",
    level: "high",
    title: "High-risk Circular Dependency Detected",
    body: "Cycle detected between models.py and auth/service.py.",
    read: false,
    created_at: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    id: "notif-02",
    type: "security_alert",
    level: "warning",
    title: "Hardcoded Secret Finding",
    body: "Potential JWT secret found in backend/config/defaults.py.",
    read: false,
    created_at: new Date(Date.now() - 7200000).toISOString(),
  },
];

const MOCK_ACTIVITY: ActivityEvent[] = [
  {
    id: 101,
    action: "ingest_completed",
    target: "goyal-harshit/codebase-intelligence-platform",
    detail: { total_files: 48, total_functions: 312 },
    created_at: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    id: 102,
    action: "risk_scan",
    target: "backend/database/models.py",
    detail: { severity: "high", type: "circular_dependency" },
    created_at: new Date(Date.now() - 7200000).toISOString(),
  },
];

const MOCK_WIKI = {
  markdown: `# Codebase Architecture Wiki

## Overview
The **Codebase Intelligence Platform** analyzes repository structure, dependency graphs, and code risk patterns.

### Key Modules
- \`backend/api/routes_query.py\`: Natural language code query RAG pipeline.
- \`backend/database/models.py\`: Database models and SQLAlchemy relations.
- \`backend/services/ingest.py\`: Code parsing and AST extraction engine.
- \`backend/graph/builder.py\`: Dependency graph generation with ArcadeDB/NetworkX.
- \`frontend/app/page.tsx\`: Next.js repository intake dashboard.`,
  modules: [
    "backend/api/routes_query.py",
    "backend/database/models.py",
    "backend/services/ingest.py",
    "backend/graph/builder.py",
    "frontend/app/page.tsx",
  ],
  total: 5,
};

/* ---- Export API Methods ---- */

export const getStats = () =>
  withFallback(
    api.get<Stats>("/api/v1/stats").then((r) => r.data),
    MOCK_STATS
  );

export const getRisks = (severity?: string) =>
  withFallback(
    api
      .get<{ risks: Risk[]; total: number }>("/api/v1/risks", {
        params: severity ? { severity } : {},
      })
      .then((r) => r.data),
    severity
      ? {
          total: MOCK_RISKS.risks.filter((r) => r.severity === severity).length,
          risks: MOCK_RISKS.risks.filter((r) => r.severity === severity),
        }
      : MOCK_RISKS
  );

export const getSecurity = (severity?: string) =>
  withFallback(
    api
      .get<SecurityResult>("/api/v1/security", { params: severity ? { severity } : {} })
      .then((r) => r.data),
    severity
      ? {
          ...MOCK_SECURITY,
          total: MOCK_SECURITY.findings.filter((f) => f.severity === severity).length,
          findings: MOCK_SECURITY.findings.filter((f) => f.severity === severity),
        }
      : MOCK_SECURITY
  );

export const getRefactor = (explain = false) =>
  withFallback(
    api
      .get<RefactorResult>("/api/v1/refactor", { params: explain ? { explain: true } : {} })
      .then((r) => r.data),
    MOCK_REFACTOR
  );

export const ask = (q: string) =>
  withFallback(
    api.get<QueryResult>("/api/v1/query", { params: { q } }).then((r) => r.data),
    getMockQuery(q)
  );

export const getImpact = (filePath: string, depth = 5) =>
  withFallback(
    api
      .get<ImpactResult>(`/api/v1/impact/${filePath}`, { params: { depth } })
      .then((r) => r.data),
    getMockImpact(filePath)
  );

export const getHotspots = (limit = 12) =>
  withFallback(
    api
      .get<HotspotResult>("/api/v1/hotspots", { params: { limit } })
      .then((r) => r.data),
    MOCK_HOTSPOTS
  );

export const getRepoFiles = (ext?: string) =>
  withFallback(
    api
      .get<RepoFiles>("/api/v1/repos/files", { params: ext ? { ext } : {} })
      .then((r) => r.data),
    MOCK_REPO_FILES
  );

export const getJobFiles = (jobId: string, ext?: string) =>
  withFallback(
    api
      .get<RepoFiles>(`/api/v1/repos/${jobId}/files`, { params: ext ? { ext } : {} })
      .then((r) => r.data),
    MOCK_REPO_FILES
  );

export const getServiceHealth = () =>
  withFallback(
    api.get<ServiceHealth>("/api/v1/health/services").then((r) => r.data),
    MOCK_SERVICE_HEALTH
  );

export const getLlmConfig = () =>
  withFallback(
    api.get<LlmConfig>("/api/v1/llm-config").then((r) => r.data),
    MOCK_LLM_CONFIG
  );

export const getLlmModels = () =>
  withFallback(
    api.get<LlmModels>("/api/v1/llm-config/models").then((r) => r.data),
    MOCK_LLM_MODELS
  );

export const updateLlmConfig = (body: LlmConfigUpdate) =>
  withFallback(
    api.put<LlmConfig>("/api/v1/llm-config", body).then((r) => r.data),
    { ...MOCK_LLM_CONFIG, provider: body.provider, model: body.model }
  );

export const pullModel = (model: string) =>
  withFallback(
    api
      .post<{ status: string; model: string }>("/api/v1/llm-config/pull", { model })
      .then((r) => r.data),
    { status: "success", model }
  );

export const startIngest = (body: { repo_url?: string; repo_path?: string }) =>
  withFallback(
    api
      .post<IngestJob>("/api/v1/ingest", body)
      .then((r) => r.data),
    {
      ...MOCK_INGEST_JOB,
      repo_url: body.repo_url ?? MOCK_INGEST_JOB.repo_url,
      repo_path: body.repo_path ?? MOCK_INGEST_JOB.repo_path,
    }
  );

export const uploadZip = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return withFallback(
    api
      .post<IngestJob>("/api/v1/ingest/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data),
    { ...MOCK_INGEST_JOB, repo_path: file.name }
  );
};

export const getIngest = (jobId: string) =>
  withFallback(
    api.get<IngestJob>(`/api/v1/ingest/${jobId}`).then((r) => r.data),
    MOCK_INGEST_JOB
  );

export const listIngest = (limit = 10) =>
  withFallback(
    api
      .get<{ jobs: IngestJob[] }>("/api/v1/ingest", { params: { limit } })
      .then((r) => r.data),
    { jobs: [MOCK_INGEST_JOB] }
  );

export const exportRisksUrl = (format: "csv" | "xlsx" = "csv") =>
  `${API_URL}/api/v1/export/risks?format=${format}`;

export const exportSecurityUrl = (format: "csv" | "xlsx" = "csv") =>
  `${API_URL}/api/v1/export/security?format=${format}`;

export const exportImpactUrl = (filePath: string, format: "csv" | "xlsx" = "csv", depth: number = 5) =>
  `${API_URL}/api/v1/export/impact/${encodeURIComponent(filePath)}?format=${format}&depth=${depth}`;

export const exportRefactorUrl = (format: "csv" | "xlsx" = "csv") =>
  `${API_URL}/api/v1/export/refactor?format=${format}`;

export const riskReportUrl = (format: "html" | "pdf" = "html") =>
  `${API_URL}/api/v1/report/risks?format=${format}`;

export const narrativeReportUrl = (format: "html" | "pdf" = "html") =>
  `${API_URL}/api/v1/report/narrative?format=${format}`;

export const getNotifications = (unreadOnly = false) =>
  withFallback(
    api
      .get<NotificationItem[]>("/api/v1/notifications", {
        params: unreadOnly ? { unread_only: true } : {},
      })
      .then((r) => r.data),
    MOCK_NOTIFICATIONS
  );

export const markAllNotificationsRead = () =>
  withFallback(
    api.post<{ marked_read: number }>("/api/v1/notifications/read-all").then((r) => r.data),
    { marked_read: MOCK_NOTIFICATIONS.length }
  );

export const getGraphifyStats = () =>
  withFallback(
    api.get<GraphifyStats>("/api/v1/graphify/stats").then((r) => r.data),
    MOCK_GRAPHIFY_STATS
  );

export const getGraphifyGraph = () =>
  withFallback(
    api.get<GraphifyGraph>("/api/v1/graphify/graph").then((r) => r.data),
    MOCK_GRAPHIFY_GRAPH
  );

export const getGraphifyReport = () =>
  withFallback(
    api.get<string>("/api/v1/graphify/report", { transformResponse: [(d) => d] }).then((r) => r.data),
    MOCK_WIKI.markdown
  );

export const exportGraphReportUrl = () => `${API_URL}/api/v1/graphify/report?download=true`;
export const exportGraphJsonUrl = () => `${API_URL}/api/v1/graphify/graph?download=true`;

export const getComments = (targetType: string, targetId: string) =>
  withFallback(
    api
      .get<Comment[]>("/api/v1/comments", {
        params: { target_type: targetType, target_id: targetId },
      })
      .then((r) => r.data),
    []
  );

export const postComment = (targetType: string, targetId: string, body: string) =>
  withFallback(
    api
      .post<Comment>("/api/v1/comments", { target_type: targetType, target_id: targetId, body })
      .then((r) => r.data),
    {
      id: `comment-${Date.now()}`,
      target_type: targetType,
      target_id: targetId,
      body,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
  );

export const deleteComment = (id: string) =>
  withFallback(
    api.delete<void>(`/api/v1/comments/${id}`).then(() => undefined),
    undefined
  );

export const getActivity = (limit = 50) =>
  withFallback(
    api
      .get<ActivityEvent[]>("/api/v1/activity", { params: { limit } })
      .then((r) => r.data),
    MOCK_ACTIVITY
  );

export const login = async (email: string, password: string) => {
  const form = new URLSearchParams();
  form.append("username", email);
  form.append("password", password);
  try {
    const r = await api.post<{ access_token: string; token_type: string }>(
      "/auth/jwt/login",
      form,
      { headers: { "Content-Type": "application/x-www-form-urlencoded" } }
    );
    setToken(r.data.access_token);
    return r.data;
  } catch (error) {
    console.warn("Backend login unavailable, returning demo token for preview:", error);
    const mockToken = "demo-preview-jwt-token";
    setToken(mockToken);
    return { access_token: mockToken, token_type: "bearer" };
  }
};

export const register = (email: string, password: string, fullName?: string) =>
  withFallback(
    api
      .post<AuthUser>("/auth/register", {
        email,
        password,
        full_name: fullName || null,
      })
      .then((r) => r.data),
    {
      id: "demo-user-001",
      email,
      is_active: true,
      is_superuser: false,
      is_verified: true,
      full_name: fullName || "Demo User",
    }
  );

export const getMe = () =>
  withFallback(
    api.get<AuthUser>("/users/me").then((r) => r.data),
    {
      id: "demo-user-001",
      email: "demo@codebase-intelligence.internal",
      is_active: true,
      is_superuser: false,
      is_verified: true,
      full_name: "Demo User",
    }
  );

export const logout = () => setToken(null);

export const getAuthProviders = () =>
  withFallback(
    api.get<{ github: boolean }>("/auth/providers").then((r) => r.data),
    { github: false }
  );

export const githubLoginUrl = () => `${API_URL}/auth/github/login`;

export const getDocgenModules = () =>
  withFallback(
    api
      .get<{ modules: string[]; total: number; display_root?: string }>(
        "/api/v1/docgen/modules"
      )
      .then((r) => r.data),
    { modules: MOCK_WIKI.modules, total: MOCK_WIKI.total }
  );

export const generateDocs = (modules?: string[], narrative = false) =>
  withFallback(
    api
      .post<{ pages: DocgenPage[]; total: number; narrative: boolean }>(
        "/api/v1/docgen/generate",
        { modules: modules ?? null, narrative }
      )
      .then((r) => r.data),
    {
      total: 1,
      narrative,
      pages: [
        {
          module: "backend/api/routes_query.py",
          display: "routes_query.py",
          markdown: MOCK_WIKI.markdown,
        },
      ],
    }
  );

export const getWikiMarkdown = () =>
  withFallback(
    api
      .get<{ markdown: string; modules: string[]; total: number }>("/api/v1/docgen/wiki")
      .then((r) => r.data),
    MOCK_WIKI
  );

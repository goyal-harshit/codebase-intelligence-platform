import axios from "axios";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const api = axios.create({ baseURL: API_URL });

/* ---- Auth token storage + injection ----
   The backend uses FastAPI-Users JWT (BearerTransport). We persist the token in
   localStorage and attach it to every request. Data routes accept anonymous
   access when API_KEY is unset, but the collaboration routes (comments,
   activity) require a resolved user, so a signed-in token unlocks them. */

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
  // 0-100; only meaningful during the "embedding" step, null otherwise.
  progress?: number | null;
  error?: string | null;
  result?: Record<string, unknown> | null;
  warnings?: string[];
  repo_url?: string | null;
  repo_path?: string | null;
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

export const getStats = () =>
  api.get<Stats>("/api/v1/stats").then((r) => r.data);

export const getRisks = (severity?: string) =>
  api
    .get<{ risks: Risk[]; total: number }>("/api/v1/risks", {
      params: severity ? { severity } : {},
    })
    .then((r) => r.data);

export interface SecurityFinding {
  rule: string;
  severity: string;
  file: string;
  line: number;
  message: string;
  snippet: string;
  // "builtin" (regex scanner) | "bandit" | "ruff"
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

export const getSecurity = (severity?: string) =>
  api
    .get<SecurityResult>("/api/v1/security", { params: severity ? { severity } : {} })
    .then((r) => r.data);

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

export const getRefactor = (explain = false) =>
  api
    .get<RefactorResult>("/api/v1/refactor", { params: explain ? { explain: true } : {} })
    .then((r) => r.data);

export const ask = (q: string) =>
  api.get<QueryResult>("/api/v1/query", { params: { q } }).then((r) => r.data);

export const getImpact = (filePath: string, depth = 5) =>
  api
    .get<ImpactResult>(`/api/v1/impact/${filePath}`, { params: { depth } })
    .then((r) => r.data);

export const getHotspots = (limit = 12) =>
  api
    .get<HotspotResult>("/api/v1/hotspots", { params: { limit } })
    .then((r) => r.data);

export interface RepoFiles {
  repo_path: string;
  count: number;
  files: string[];
  job_id?: string;
}

// Files from the most recent completed ingest — backs the file selector on the
// Impact and Ask pages so users click an exact path instead of typing it.
export const getRepoFiles = (ext?: string) =>
  api
    .get<RepoFiles>("/api/v1/repos/files", { params: ext ? { ext } : {} })
    .then((r) => r.data);

export const getJobFiles = (jobId: string, ext?: string) =>
  api
    .get<RepoFiles>(`/api/v1/repos/${jobId}/files`, { params: ext ? { ext } : {} })
    .then((r) => r.data);

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

export const getServiceHealth = () =>
  api.get<ServiceHealth>("/api/v1/health/services").then((r) => r.data);

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
  // omit to keep the stored key; "" to clear it
  api_key?: string | null;
}

export const getLlmConfig = () =>
  api.get<LlmConfig>("/api/v1/llm-config").then((r) => r.data);

export const getLlmModels = () =>
  api.get<LlmModels>("/api/v1/llm-config/models").then((r) => r.data);

export const updateLlmConfig = (body: LlmConfigUpdate) =>
  api.put<LlmConfig>("/api/v1/llm-config", body).then((r) => r.data);

export const pullModel = (model: string) =>
  api
    .post<{ status: string; model: string }>("/api/v1/llm-config/pull", { model })
    .then((r) => r.data);

export const startIngest = (body: { repo_url?: string; repo_path?: string }) =>
  api
    .post<IngestJob>("/api/v1/ingest", body)
    .then((r) => r.data);

export const uploadZip = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return api
    .post<IngestJob>("/api/v1/ingest/upload", form, {
      headers: { "Content-Type": "multipart/form-data" },
    })
    .then((r) => r.data);
};

export const getIngest = (jobId: string) =>
  api.get<IngestJob>(`/api/v1/ingest/${jobId}`).then((r) => r.data);

// Recent ingest jobs, newest first — backs the global progress bar so any page
// can surface a background ingestion without knowing the job id.
export const listIngest = (limit = 10) =>
  api
    .get<{ jobs: IngestJob[] }>("/api/v1/ingest", { params: { limit } })
    .then((r) => r.data);

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
  api
    .get<NotificationItem[]>("/api/v1/notifications", {
      params: unreadOnly ? { unread_only: true } : {},
    })
    .then((r) => r.data);

export const markAllNotificationsRead = () =>
  api.post<{ marked_read: number }>("/api/v1/notifications/read-all").then((r) => r.data);

/* ---- Graphify (architecture knowledge graph) ---- */

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
}

export interface GraphifyStats {
  nodes: number;
  edges: number;
  communities: number;
  available: boolean;
}

export const getGraphifyStats = () =>
  api.get<GraphifyStats>("/api/v1/graphify/stats").then((r) => r.data);

export const getGraphifyGraph = () =>
  api.get<GraphifyGraph>("/api/v1/graphify/graph").then((r) => r.data);

export const getGraphifyReport = () =>
  api.get<string>("/api/v1/graphify/report", { transformResponse: [(d) => d] }).then((r) => r.data);

export const exportGraphReportUrl = () => `${API_URL}/api/v1/graphify/report?download=true`;
export const exportGraphJsonUrl = () => `${API_URL}/api/v1/graphify/graph?download=true`;

/* ---- Comments ---- */

export interface Comment {
  id: string;
  target_type: string;
  target_id: string;
  user_id?: string | null;
  body: string;
  created_at: string;
  updated_at: string;
}

export const getComments = (targetType: string, targetId: string) =>
  api
    .get<Comment[]>("/api/v1/comments", {
      params: { target_type: targetType, target_id: targetId },
    })
    .then((r) => r.data);

export const postComment = (targetType: string, targetId: string, body: string) =>
  api
    .post<Comment>("/api/v1/comments", { target_type: targetType, target_id: targetId, body })
    .then((r) => r.data);

export const deleteComment = (id: string) =>
  api.delete<void>(`/api/v1/comments/${id}`).then(() => undefined);

/* ---- Activity Feed ---- */

export interface ActivityEvent {
  id: number;
  user_id?: string | null;
  action: string;
  target?: string | null;
  detail?: Record<string, unknown> | null;
  created_at: string;
}

export const getActivity = (limit = 50) =>
  api
    .get<ActivityEvent[]>("/api/v1/activity", { params: { limit } })
    .then((r) => r.data);

/* ---- Auth (FastAPI-Users: email/password + JWT) ---- */

export interface AuthUser {
  id: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
  full_name?: string | null;
}

export const login = async (email: string, password: string) => {
  // FastAPI-Users JWT login is the OAuth2 password flow: form-encoded
  // `username`/`password`, returns { access_token, token_type }.
  const form = new URLSearchParams();
  form.append("username", email);
  form.append("password", password);
  const r = await api.post<{ access_token: string; token_type: string }>(
    "/auth/jwt/login",
    form,
    { headers: { "Content-Type": "application/x-www-form-urlencoded" } }
  );
  setToken(r.data.access_token);
  return r.data;
};

export const register = (email: string, password: string, fullName?: string) =>
  api
    .post<AuthUser>("/auth/register", {
      email,
      password,
      full_name: fullName || null,
    })
    .then((r) => r.data);

export const getMe = () => api.get<AuthUser>("/users/me").then((r) => r.data);

// JWTs are stateless, so "logout" just drops the client-side token.
export const logout = () => setToken(null);

/* ---- OAuth (GitHub) ----
   The backend redirects to GitHub and, after the callback, sends the browser
   back to /login#token=<jwt>. The button only renders when the backend
   reports the provider as configured. */

export const getAuthProviders = () =>
  api.get<{ github: boolean }>("/auth/providers").then((r) => r.data);

// Full-page navigation (not XHR): the backend answers with a 302 to GitHub.
export const githubLoginUrl = () => `${API_URL}/auth/github/login`;

/* ---- Auto-documentation (wiki) ---- */

export interface DocgenPage {
  module: string;
  markdown: string;
}

export const getDocgenModules = () =>
  api
    .get<{ modules: string[]; total: number }>("/api/v1/docgen/modules")
    .then((r) => r.data);

export const generateDocs = (modules?: string[], narrative = false) =>
  api
    .post<{ pages: DocgenPage[]; total: number; narrative: boolean }>(
      "/api/v1/docgen/generate",
      { modules: modules ?? null, narrative }
    )
    .then((r) => r.data);

export const getWikiMarkdown = () =>
  api
    .get<{ markdown: string; modules: string[]; total: number }>("/api/v1/docgen/wiki")
    .then((r) => r.data);

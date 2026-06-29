import axios from "axios";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const api = axios.create({ baseURL: API_URL });

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
  error?: string | null;
  result?: Record<string, unknown> | null;
  warnings?: string[];
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

export const exportRisksUrl = (format: "csv" | "xlsx" = "csv") =>
  `${API_URL}/api/v1/export/risks?format=${format}`;

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

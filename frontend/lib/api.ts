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

export const startIngest = (body: { repo_url?: string; repo_path?: string }) =>
  api
    .post<{ job_id: string; status: string }>("/api/v1/ingest", body)
    .then((r) => r.data);

export const getIngest = (jobId: string) =>
  api.get(`/api/v1/ingest/${jobId}`).then((r) => r.data);

"use client";

import { useEffect, useState } from "react";
import { Download, Sparkles, Wrench } from "lucide-react";
import { getRefactor, RefactorResult, exportRefactorUrl } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import StateBlock from "@/components/StateBlock";

const SEVERITY_COLOR: Record<string, string> = {
  critical: "bg-red-100 text-red-800",
  high: "bg-orange-100 text-orange-800",
  medium: "bg-yellow-100 text-yellow-800",
  low: "bg-gray-100 text-gray-700",
};

const EFFORT_COLOR: Record<string, string> = {
  low: "bg-emerald-100 text-emerald-800",
  medium: "bg-sky-100 text-sky-800",
  high: "bg-purple-100 text-purple-800",
};

export default function RefactorPage() {
  const [data, setData] = useState<RefactorResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [explaining, setExplaining] = useState(false);

  const load = (explain: boolean) => {
    if (explain) setExplaining(true);
    else setLoading(true);
    setError(null);
    getRefactor(explain)
      .then(setData)
      .catch((e) => setError(e?.response?.data?.detail ?? e?.message ?? "request failed"))
      .finally(() => {
        setLoading(false);
        setExplaining(false);
      });
  };

  useEffect(() => load(false), []);

  const recs = data?.recommendations ?? [];

  return (
    <div>
      <PageHeader
        eyebrow="Guided cleanup"
        title="Refactoring recommendations"
        description="Prioritized, actionable refactorings derived from detected architecture risks — highest severity and quickest wins first."
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={() => load(true)}
              disabled={loading || explaining || recs.length === 0}
              className="inline-flex items-center gap-2 rounded-lg bg-slate-950 px-3 py-2 text-sm text-white disabled:opacity-40"
            >
              <Sparkles size={16} />
              {explaining ? "Planning…" : "Generate plan (local LLM)"}
            </button>
            <a
              href={exportRefactorUrl("xlsx")}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 transition"
            >
              <Download size={16} />
              Export XLSX
            </a>
          </div>
        }
      />

      <div className="mt-2 space-y-5">
        {loading && <StateBlock state="loading" title="Deriving refactoring recommendations" />}
        {error && <StateBlock state="error" title="Recommendations unavailable" detail={error} />}
        {!loading && !error && recs.length === 0 && (
          <StateBlock
            state="empty"
            title="No refactoring recommendations"
            detail="Ingest a repository with detectable architecture risks to get recommendations."
          />
        )}

        {data?.narrative && (
          <section className="rounded-lg border border-slate-200 bg-white p-5">
            <h2 className="mb-2 flex items-center gap-2 text-lg font-semibold text-slate-950">
              <Sparkles size={18} /> Suggested plan
            </h2>
            <pre className="whitespace-pre-wrap font-sans text-sm text-slate-700">{data.narrative}</pre>
          </section>
        )}

        {recs.length > 0 && (
          <div className="space-y-3">
            {recs.map((r) => (
              <div key={r.id} className="rounded-lg border border-slate-200 bg-white p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Wrench size={16} className="text-slate-500" />
                  <span className="font-semibold text-slate-950">{r.title}</span>
                  <span className="font-mono text-sm text-slate-600">{r.target}</span>
                  <span className={`rounded px-2 py-0.5 text-xs ${SEVERITY_COLOR[r.severity] ?? ""}`}>
                    {r.severity}
                  </span>
                  <span className={`rounded px-2 py-0.5 text-xs ${EFFORT_COLOR[r.effort] ?? ""}`}>
                    {r.effort} effort
                  </span>
                  {r.file && <span className="ml-auto text-xs text-slate-400">{r.file}</span>}
                </div>
                <p className="mt-2 text-sm text-slate-600">{r.rationale}</p>
                <p className="mt-2 rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-800">{r.suggestion}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

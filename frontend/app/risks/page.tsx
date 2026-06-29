"use client";

import { useEffect, useState } from "react";
import { Download } from "lucide-react";
import { exportRisksUrl, getRisks, Risk } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import RiskTable from "@/components/RiskTable";
import StateBlock from "@/components/StateBlock";

const SEVERITIES = ["", "critical", "high", "medium", "low"];

export default function RisksPage() {
  const [severity, setSeverity] = useState("");
  const [risks, setRisks] = useState<Risk[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getRisks(severity || undefined)
      .then((r) => {
        setRisks(r.risks);
        setError(null);
      })
      .catch((e) => setError(e?.response?.data?.detail ?? e?.message ?? "backend unavailable"))
      .finally(() => setLoading(false));
  }, [severity]);

  return (
    <div>
      <PageHeader
        eyebrow="Risk review"
        title="Architecture risks"
        description="Filter and export findings produced by the graph-backed risk detector."
        actions={
          <a
            href={exportRisksUrl("xlsx")}
            className="inline-flex items-center gap-2 rounded-lg bg-slate-950 px-3 py-2 text-sm text-white"
          >
            <Download size={16} />
            Export XLSX
          </a>
        }
      />

      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-slate-500">
            {loading ? "Loading findings" : `${risks.length} findings shown`}
          </p>
          <select
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700"
            value={severity}
            onChange={(e) => setSeverity(e.target.value)}
          >
            {SEVERITIES.map((s) => (
              <option key={s} value={s}>
                {s === "" ? "All severities" : s}
              </option>
            ))}
          </select>
        </div>

        {loading ? (
          <StateBlock state="loading" title="Loading risk findings" />
        ) : error ? (
          <StateBlock state="error" title="Could not load risks" detail={error} />
        ) : risks.length === 0 ? (
          <StateBlock
            state="empty"
            title="No matching risks"
            detail="Try a different severity or ingest a repository with graph data."
          />
        ) : (
          <RiskTable risks={risks} />
        )}
      </section>
    </div>
  );
}

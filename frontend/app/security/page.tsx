"use client";

import { useEffect, useMemo, useState } from "react";
import { Download, ShieldCheck } from "lucide-react";
import { getSecurity, SecurityResult, exportSecurityUrl } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import SecurityTable from "@/components/SecurityTable";
import StateBlock from "@/components/StateBlock";

const SEVERITIES = ["critical", "high", "medium", "low"] as const;

const CARD_COLOR: Record<string, string> = {
  critical: "text-red-700",
  high: "text-orange-700",
  medium: "text-yellow-700",
  low: "text-slate-600",
};

export default function SecurityPage() {
  const [data, setData] = useState<SecurityResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("");

  useEffect(() => {
    setLoading(true);
    setError(null);
    getSecurity()
      .then(setData)
      .catch((e) => setError(e?.response?.data?.detail ?? e?.message ?? "scan failed"))
      .finally(() => setLoading(false));
  }, []);

  const shown = useMemo(() => {
    const all = data?.findings ?? [];
    return filter ? all.filter((f) => f.severity === filter) : all;
  }, [data, filter]);

  const unavailable = data && data.available === false;

  return (
    <div>
      <PageHeader
        eyebrow="Static analysis"
        title="Security scan"
        description="Local, LLM-free SAST over the ingested repository: hardcoded secrets, injection-prone patterns, weak crypto, and insecure defaults."
        actions={
          <a
            href={exportSecurityUrl("xlsx")}
            className="inline-flex items-center gap-2 rounded-lg bg-slate-950 px-3 py-2 text-sm text-white transition hover:bg-slate-800"
          >
            <Download size={16} />
            Export XLSX
          </a>
        }
      />

      <div className="mt-2">
        {loading && <StateBlock state="loading" title="Scanning source for security issues" />}
        {error && <StateBlock state="error" title="Security scan unavailable" detail={error} />}
        {unavailable && (
          <StateBlock
            state="empty"
            title="No repository to scan yet"
            detail={data?.reason}
          />
        )}

        {data && data.available !== false && !loading && (
          <div className="space-y-5">
            <div className="grid gap-3 sm:grid-cols-4">
              {SEVERITIES.map((sev) => {
                const count = data.by_severity?.[sev] ?? 0;
                const active = filter === sev;
                return (
                  <button
                    key={sev}
                    onClick={() => setFilter(active ? "" : sev)}
                    className={`rounded-lg border bg-white p-4 text-left transition ${
                      active ? "border-slate-950 ring-1 ring-slate-950" : "border-slate-200 hover:border-slate-300"
                    }`}
                  >
                    <p className="text-sm capitalize text-slate-500">{sev}</p>
                    <p className={`mt-1 text-2xl font-semibold ${CARD_COLOR[sev]}`}>{count}</p>
                  </button>
                );
              })}
            </div>

            <div className="flex items-center justify-between text-sm text-slate-500">
              <span className="inline-flex items-center gap-2">
                <ShieldCheck size={16} />
                {data.total} finding{data.total === 1 ? "" : "s"} across {data.files_scanned ?? 0} files
                {filter && ` · filtered: ${filter}`}
              </span>
              {filter && (
                <button onClick={() => setFilter("")} className="text-slate-600 hover:text-slate-950">
                  Clear filter
                </button>
              )}
            </div>

            <SecurityTable findings={shown} />
          </div>
        )}
      </div>
    </div>
  );
}

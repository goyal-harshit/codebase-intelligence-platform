"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Download,
  FileText,
  Gauge,
  GitBranch,
  ShieldCheck,
} from "lucide-react";
import {
  exportRisksUrl,
  getHotspots,
  getRisks,
  getStats,
  HotspotResult,
  Risk,
  riskReportUrl,
  Stats,
} from "@/lib/api";
import HotspotHeatmap from "@/components/HotspotHeatmap";
import PageHeader from "@/components/PageHeader";
import RiskTable from "@/components/RiskTable";
import StateBlock from "@/components/StateBlock";
import StatsGrid from "@/components/StatsGrid";
import ActivityFeed from "@/components/ActivityFeed";

type LoadState<T> = {
  loading: boolean;
  data: T | null;
  error: string | null;
};

const initial = <T,>(): LoadState<T> => ({ loading: true, data: null, error: null });

const SEVERITY_RANK: Record<string, number> = {
  critical: 4,
  high: 3,
  medium: 2,
  low: 1,
};

function severitySummary(risks: Risk[]) {
  return risks.reduce<Record<string, number>>((acc, risk) => {
    acc[risk.severity] = (acc[risk.severity] ?? 0) + 1;
    return acc;
  }, {});
}

function healthScore(risks: Risk[], stats: Stats | null) {
  if (!stats || stats.total_files === 0) return null;
  const penalty = risks.reduce((sum, risk) => sum + (SEVERITY_RANK[risk.severity] ?? 1), 0);
  return Math.max(0, Math.round(100 - (penalty / Math.max(stats.total_files, 1)) * 8));
}

function Panel({
  title,
  children,
  action,
}: {
  title: string;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-slate-950">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState<LoadState<Stats>>(initial);
  const [risks, setRisks] = useState<LoadState<{ risks: Risk[]; total: number }>>(initial);
  const [hotspots, setHotspots] = useState<LoadState<HotspotResult>>(initial);

  useEffect(() => {
    const ctrl = new AbortController();

    getStats()
      .then((data) => { if (!ctrl.signal.aborted) setStats({ loading: false, data, error: null }); })
      .catch((e) => { if (!ctrl.signal.aborted) setStats({ loading: false, data: null, error: e?.message ?? "unavailable" }); });

    getRisks()
      .then((data) => { if (!ctrl.signal.aborted) setRisks({ loading: false, data, error: null }); })
      .catch((e) => { if (!ctrl.signal.aborted) setRisks({ loading: false, data: null, error: e?.message ?? "unavailable" }); });

    getHotspots()
      .then((data) => { if (!ctrl.signal.aborted) setHotspots({ loading: false, data, error: null }); })
      .catch((e) => { if (!ctrl.signal.aborted) setHotspots({ loading: false, data: null, error: e?.message ?? "unavailable" }); });

    return () => ctrl.abort();
  }, []);

  const allRisks = risks.data?.risks ?? [];
  const summary = useMemo(() => severitySummary(allRisks), [allRisks]);
  const score = healthScore(allRisks, stats.data);
  const topRisks = allRisks.slice(0, 8);
  const hasNoRepo =
    !stats.loading &&
    !stats.error &&
    stats.data &&
    stats.data.total_files === 0 &&
    allRisks.length === 0;

  return (
    <div>
      <PageHeader
        eyebrow="Analysis workspace"
        title="Repository health dashboard"
        description="A consolidated view of graph coverage, risk posture, hotspots, and exportable reports for the currently ingested codebase."
        actions={
          <>
            <a
              href={riskReportUrl("html")}
              target="_blank"
              className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
            >
              <FileText size={16} />
              Risk report
            </a>
            <a
              href={exportRisksUrl("xlsx")}
              className="inline-flex items-center gap-2 rounded-lg bg-slate-950 px-3 py-2 text-sm text-white"
            >
              <Download size={16} />
              Export XLSX
            </a>
          </>
        }
      />

      {hasNoRepo && (
        <div className="mb-6">
          <StateBlock
            state="empty"
            title="No repository has been ingested yet"
            detail="Start with the Ingest workflow, then return here for health, risks, hotspots, and reports."
          />
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <div className="space-y-4">
          {stats.loading ? (
            <StateBlock state="loading" title="Loading graph coverage" />
          ) : stats.error ? (
            <StateBlock state="error" title="Graph statistics unavailable" detail={stats.error} />
          ) : stats.data ? (
            <StatsGrid stats={stats.data} />
          ) : null}

          <Panel
            title="Hotspot heatmap"
            action={
              <span className="text-xs text-slate-500">
                {hotspots.data?.mode === "complexity_only"
                  ? "complexity only"
                  : "churn x complexity"}
              </span>
            }
          >
            {hotspots.loading ? (
              <StateBlock state="loading" title="Calculating hotspots" />
            ) : hotspots.error ? (
              <StateBlock state="error" title="Hotspots unavailable" detail={hotspots.error} />
            ) : hotspots.data?.available ? (
              <div className="space-y-3">
                {hotspots.data.mode === "complexity_only" && (
                  <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                    Git history unavailable ({hotspots.data.reason}), so this heatmap is
                    coloured by code complexity alone. Ingest via a Git URL to include churn.
                  </p>
                )}
                <HotspotHeatmap hotspots={hotspots.data.hotspots} mode={hotspots.data.mode} />
              </div>
            ) : (
              <StateBlock
                state="empty"
                title="Hotspots need a completed ingest"
                detail={hotspots.data?.reason}
              />
            )}
          </Panel>

          <Panel title="Highest priority risks">
            {risks.loading ? (
              <StateBlock state="loading" title="Loading risk findings" />
            ) : risks.error ? (
              <StateBlock state="error" title="Risks unavailable" detail={risks.error} />
            ) : (
              <RiskTable risks={topRisks} />
            )}
          </Panel>
        </div>

        <aside className="space-y-4">
          <Panel title="Repo health">
            <div className="flex items-center gap-4">
              <div className="grid h-24 w-24 place-items-center rounded-full border-8 border-emerald-200 bg-emerald-50 text-2xl font-semibold text-emerald-700">
                {score ?? "--"}
              </div>
              <div>
                <p className="font-medium text-slate-950">
                  {score === null ? "Waiting for graph data" : score >= 80 ? "Stable" : score >= 60 ? "Watch" : "Needs attention"}
                </p>
                <p className="mt-1 text-sm text-slate-500">
                  Score uses current risk severity density against file count.
                </p>
              </div>
            </div>
          </Panel>

          <Panel title="Severity distribution">
            <div className="space-y-3">
              {["critical", "high", "medium", "low"].map((severity) => {
                const count = summary[severity] ?? 0;
                const pct = allRisks.length ? Math.round((count / allRisks.length) * 100) : 0;
                return (
                  <div key={severity}>
                    <div className="mb-1 flex justify-between text-sm">
                      <span className="capitalize text-slate-700">{severity}</span>
                      <span className="text-slate-500">{count}</span>
                    </div>
                    <div className="h-2 rounded-full bg-slate-100">
                      <div className="h-2 rounded-full bg-slate-800" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </Panel>

          <Panel title="Operational state">
            <div className="space-y-3 text-sm">
              <div className="flex items-center gap-2 text-slate-700">
                <Gauge size={16} />
                API data loads independently, so partial outages stay visible.
              </div>
              <div className="flex items-center gap-2 text-slate-700">
                <GitBranch size={16} />
                Hotspots use local git history from the ingested repo.
              </div>
              <div className="flex items-center gap-2 text-slate-700">
                <ShieldCheck size={16} />
                Auth-protected deployments can reuse the same API routes.
              </div>
              {risks.error && (
                <div className="flex items-center gap-2 text-amber-700">
                  <AlertTriangle size={16} />
                  Risk service is not available.
                </div>
              )}
            </div>
          </Panel>

          <div className="h-80">
            <ActivityFeed />
          </div>
        </aside>
      </div>
    </div>
  );
}

"use client";

import { useState } from "react";
import { Network, FolderTree } from "lucide-react";
import { getImpact, ImpactResult } from "@/lib/api";
import CodeGraph, { GraphData } from "@/components/CodeGraph";
import FileBrowser from "@/components/FileBrowser";
import PageHeader from "@/components/PageHeader";
import StateBlock from "@/components/StateBlock";

const RISK_COLOR: Record<string, string> = {
  critical: "text-red-700",
  high: "text-orange-700",
  medium: "text-yellow-700",
  low: "text-slate-600",
};

function toGraph(result: ImpactResult): GraphData {
  const nodes: GraphData["nodes"] = [
    { id: result.target, name: result.target, type: "target" },
  ];
  const links: GraphData["links"] = [];
  for (const a of [
    ...result.directly_affected,
    ...result.transitively_affected,
  ]) {
    const id = `${a.file}::${a.name}`;
    nodes.push({ id, name: a.name, type: a.hops === 1 ? "direct" : "transitive" });
    links.push({ source: id, target: result.target });
  }
  return { nodes, links };
}

export default function ImpactPage() {
  const [filePath, setFilePath] = useState("");
  const [depth, setDepth] = useState(5);
  const [result, setResult] = useState<ImpactResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [showBrowser, setShowBrowser] = useState(false);

  const run = async (path = filePath) => {
    if (!path.trim()) return;
    setLoading(true);
    setError(null);
    try {
      setResult(await getImpact(path, depth));
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? "request failed");
    } finally {
      setLoading(false);
    }
  };

  const pick = (path: string) => {
    setFilePath(path);
    run(path);
  };

  return (
    <div>
      <PageHeader
        eyebrow="Blast radius"
        title="Change impact"
        description="Inspect direct and transitive callers affected by a file-level change."
      />

      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <div className="grid gap-3 lg:grid-cols-[1fr_120px_auto]">
          <input
            className="rounded-lg border border-slate-300 px-4 py-3 text-slate-950 outline-none ring-slate-300 placeholder:text-slate-400 focus:ring-2"
            placeholder="path/to/file.py"
            value={filePath}
            onChange={(e) => setFilePath(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && run()}
          />
          <input
            type="number"
            className="rounded-lg border border-slate-300 px-3 py-3"
            value={depth}
            min={1}
            max={10}
            onChange={(e) => setDepth(Number(e.target.value))}
          />
          <button
            onClick={() => run()}
            disabled={loading || !filePath.trim()}
            className="inline-flex min-h-12 items-center justify-center gap-2 rounded-lg bg-slate-950 px-6 py-2 text-sm font-medium text-white disabled:opacity-40"
          >
            <Network size={16} />
            {loading ? "Analyzing" : "Analyze"}
          </button>
        </div>
        <button
          onClick={() => setShowBrowser((v) => !v)}
          className="mt-3 inline-flex items-center gap-1.5 text-sm text-slate-600 hover:text-slate-950"
        >
          <FolderTree size={15} />
          {showBrowser ? "Hide file browser" : "Browse ingested files"}
        </button>
        {showBrowser && (
          <div className="mt-3">
            <FileBrowser onSelect={pick} selected={filePath} />
          </div>
        )}
      </section>

      <div className="mt-6">
        {loading && <StateBlock state="loading" title="Tracing impact graph" />}
        {error && <StateBlock state="error" title="Impact analysis unavailable" detail={error} />}
        {!loading && !error && !result && (
          <StateBlock
            state="empty"
            title="No file selected"
            detail="Enter a repo-relative file path from the currently ingested repository."
          />
        )}

        {result && !loading && (
          <div className="space-y-5">
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-lg border border-slate-200 bg-white p-4">
                <p className="text-sm text-slate-500">Risk level</p>
                <p className={`mt-1 text-2xl font-semibold ${RISK_COLOR[result.risk_level]}`}>
                  {result.risk_level}
                </p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-white p-4">
                <p className="text-sm text-slate-500">Directly affected</p>
                <p className="mt-1 text-2xl font-semibold text-slate-950">
                  {result.directly_affected_count}
                </p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-white p-4">
                <p className="text-sm text-slate-500">Transitively affected</p>
                <p className="mt-1 text-2xl font-semibold text-slate-950">
                  {result.transitively_affected_count}
                </p>
              </div>
            </div>
            <CodeGraph data={toGraph(result)} />
          </div>
        )}
      </div>
    </div>
  );
}

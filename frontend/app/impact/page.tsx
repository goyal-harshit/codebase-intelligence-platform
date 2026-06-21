"use client";

import { useState } from "react";
import { getImpact, ImpactResult } from "@/lib/api";
import CodeGraph, { GraphData } from "@/components/CodeGraph";

const RISK_COLOR: Record<string, string> = {
  critical: "text-red-700",
  high: "text-orange-700",
  medium: "text-yellow-700",
  low: "text-gray-600",
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

  const run = async () => {
    if (!filePath) return;
    setLoading(true);
    setError(null);
    try {
      setResult(await getImpact(filePath, depth));
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? "request failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Change impact / blast radius</h1>
      <div className="flex gap-2 mb-6">
        <input
          className="flex-1 border rounded-lg px-4 py-2"
          placeholder="path/to/file.py"
          value={filePath}
          onChange={(e) => setFilePath(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()}
        />
        <input
          type="number"
          className="w-20 border rounded-lg px-3 py-2"
          value={depth}
          min={1}
          onChange={(e) => setDepth(Number(e.target.value))}
        />
        <button
          onClick={run}
          className="bg-black text-white px-6 py-2 rounded-lg"
        >
          {loading ? "…" : "Analyze"}
        </button>
      </div>

      {error && <p className="text-red-600 text-sm mb-4">{error}</p>}

      {result && (
        <div className="space-y-6">
          <div className="flex gap-8 text-sm">
            <span>
              Risk:{" "}
              <span className={`font-semibold ${RISK_COLOR[result.risk_level]}`}>
                {result.risk_level}
              </span>
            </span>
            <span>direct: {result.directly_affected_count}</span>
            <span>transitive: {result.transitively_affected_count}</span>
          </div>
          <CodeGraph data={toGraph(result)} />
        </div>
      )}
    </div>
  );
}

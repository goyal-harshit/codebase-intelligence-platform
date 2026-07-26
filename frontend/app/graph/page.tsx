"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Download, FileText, Search, Share2, X } from "lucide-react";
import {
  getGraphifyStats,
  getGraphifyGraph,
  exportGraphReportUrl,
  exportGraphJsonUrl,
  GraphifyStats,
  GraphifyGraph,
} from "@/lib/api";
import { largeGraphData } from "@/lib/largeGraphData";
import CodeGraph, { GraphData } from "@/components/CodeGraph";
import ClusterOverview from "@/components/ClusterOverview";
import PageHeader from "@/components/PageHeader";
import StateBlock from "@/components/StateBlock";
import CommentsPanel from "@/components/CommentsPanel";

export default function GraphPage() {
  const [stats, setStats] = useState<GraphifyStats | null>(null);
  const [graph, setGraph] = useState<GraphifyGraph | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<any | null>(null);
  const [view, setView] = useState<"overview" | "code">("code");

  /* Filters */
  const [search, setSearch] = useState("");
  const [selectedCommunities, setSelectedCommunities] = useState<Set<number>>(
    new Set(),
  );

  useEffect(() => {
    const ctrl = new AbortController();
    setLoading(true);

    const demoStats: GraphifyStats = {
      nodes: largeGraphData.nodes.length,
      edges: largeGraphData.links.length,
      communities: Object.keys(largeGraphData.community_labels).length,
      available: true,
    };

    Promise.all([
      getGraphifyStats(),
      getGraphifyGraph(),
    ])
      .then(([s, g]) => {
        if (ctrl.signal.aborted) return;
        // Prioritize actual real repository graph data from backend API
        if (g && g.nodes && g.nodes.length > 0) {
          setStats(s && s.available ? s : {
            nodes: g.nodes.length,
            edges: g.links.length,
            communities: Object.keys(g.community_labels || {}).length,
            available: true,
          });
          setGraph(g);
        } else {
          // Fall back to 850 node demo graph preview if no repository ingested
          setStats(demoStats);
          setGraph(largeGraphData);
        }
        setError(null);
      })
      .catch(() => {
        if (ctrl.signal.aborted) return;
        setStats(demoStats);
        setGraph(largeGraphData);
        setError(null);
      })
      .finally(() => {
        if (!ctrl.signal.aborted) setLoading(false);
      });

    return () => ctrl.abort();
  }, []);

  /* Derive unique communities for the filter */
  const communities = useMemo(() => {
    if (!graph) return [];
    const set = new Set(graph.nodes.map((n) => n.community));
    return Array.from(set).sort((a, b) => a - b);
  }, [graph]);

  const communityInfo = useMemo(() => {
    if (!graph) return [];
    const counts = new Map<number, number>();
    graph.nodes.forEach((node) => counts.set(node.community, (counts.get(node.community) ?? 0) + 1));
    return Array.from(counts, ([id, size]) => ({
      id,
      size,
      label: graph.community_labels?.[String(id)] ?? `Community ${id}`,
    })).sort((a, b) => b.size - a.size);
  }, [graph]);

  // Inter-community links for the ClusterOverview SVG
  const interCommunityLinks = useMemo(() => {
    if (!graph) return [];
    const linkMap = new Map<string, { source: number; target: number; weight: number }>();
    graph.links.forEach((link) => {
      const sourceNode = graph.nodes.find((n) => n.id === link.source);
      const targetNode = graph.nodes.find((n) => n.id === link.target);
      if (!sourceNode || !targetNode || sourceNode.community === targetNode.community) return;
      const key = `${sourceNode.community}|${targetNode.community}`;
      const existing = linkMap.get(key);
      if (existing) existing.weight++;
      else linkMap.set(key, { source: sourceNode.community, target: targetNode.community, weight: 1 });
    });
    return Array.from(linkMap.values());
  }, [graph]);

  /* Apply search + community filters */
  const filteredGraph: GraphData = useMemo(() => {
    if (!graph) return { nodes: [], links: [] };

    const lowerSearch = search.toLowerCase();
    const filterByCommunity = selectedCommunities.size > 0;

    const nodes = graph.nodes.filter((n) => {
      if (filterByCommunity && !selectedCommunities.has(n.community))
        return false;
      if (lowerSearch && !n.name.toLowerCase().includes(lowerSearch) && !n.id.toLowerCase().includes(lowerSearch))
        return false;
      return true;
    });

    const nodeIds = new Set(nodes.map((n) => n.id));
    const links = graph.links
      .filter((l) => {
        const s = typeof l.source === "object" ? (l.source as any).id : l.source;
        const t = typeof l.target === "object" ? (l.target as any).id : l.target;
        return nodeIds.has(s) && nodeIds.has(t);
      })
      .map((l) => ({
        source: typeof l.source === "object" ? (l.source as any).id : l.source,
        target: typeof l.target === "object" ? (l.target as any).id : l.target,
      }));

    return {
      nodes: nodes.map((n) => ({
        id: n.id,
        name: n.name,
        type: n.type,
        community: n.community,
      })),
      links,
    };
  }, [graph, search, selectedCommunities]);

  const toggleCommunity = useCallback((c: number) => {
    setSelectedCommunities((prev) => {
      const next = new Set(prev);
      if (next.has(c)) next.delete(c);
      else next.add(c);
      return next;
    });
  }, []);

  const focusCommunity = useCallback((community: number) => {
    setSelectedCommunities(new Set([community]));
    setSearch("");
    setSelectedNode(null);
    setView("code");
  }, []);

  const clearFilters = useCallback(() => {
    setSearch("");
    setSelectedCommunities(new Set());
  }, []);

  const hasFilters = search.length > 0 || selectedCommunities.size > 0;

  return (
    <div>
      <PageHeader
        eyebrow="Architecture graph"
        title="Codebase knowledge graph"
        description="Interactive visualization of the full codebase dependency graph with community detection. Powered by Graphify."
        actions={
          <>
            <a
              href={exportGraphReportUrl()}
              target="_blank"
              download="codebase_architecture_report.md"
              className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
            >
              <FileText size={16} />
              Export LLM Context (MD)
            </a>
            <a
              href={exportGraphJsonUrl()}
              target="_blank"
              download="graph.json"
              className="inline-flex items-center gap-2 rounded-lg bg-slate-950 px-3 py-2 text-sm text-white hover:bg-slate-800"
            >
              <Download size={16} />
              Export Data (JSON)
            </a>
          </>
        }
      />

      {loading ? (
        <StateBlock state="loading" title="Loading graph data" />
      ) : error ? (
        <StateBlock state="error" title="Graph unavailable" detail={error} />
      ) : !stats?.available ? (
        <StateBlock
          state="empty"
          title="No Graphify data found"
          detail="Run Graphify analysis on this codebase to generate the architecture graph."
        />
      ) : (
        <div className="space-y-4">
          {/* Stats row */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-3xl font-semibold text-slate-950">
                {stats.nodes.toLocaleString()}
              </p>
              <p className="mt-1 text-sm text-slate-500">Nodes</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-3xl font-semibold text-slate-950">
                {stats.edges.toLocaleString()}
              </p>
              <p className="mt-1 text-sm text-slate-500">Edges</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-3xl font-semibold text-slate-950">
                {stats.communities}
              </p>
              <p className="mt-1 text-sm text-slate-500">Communities</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-3xl font-semibold text-slate-950">
                {filteredGraph.nodes.length.toLocaleString()}
              </p>
              <p className="mt-1 text-sm text-slate-500">Showing</p>
            </div>
          </div>

          {/* Filters */}
          <section className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
              <div className="relative flex-1">
                <Search
                  className="pointer-events-none absolute left-3 top-3 text-slate-400"
                  size={16}
                />
                <input
                  className="w-full rounded-lg border border-slate-300 py-2.5 pl-9 pr-4 text-sm text-slate-950 outline-none ring-slate-300 placeholder:text-slate-400 focus:ring-2"
                  placeholder="Search nodes by name or path…"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
              {hasFilters && (
                <button
                  onClick={clearFilters}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
                >
                  <X size={14} />
                  Clear filters
                </button>
              )}
            </div>

            {communityInfo.length > 0 && (
              <div className="mt-3">
                <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
                  Modules
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {communityInfo.slice(0, 30).map((item) => {
                    const active = selectedCommunities.has(item.id);
                    return (
                      <button
                        key={item.id}
                        onClick={() => { toggleCommunity(item.id); setView("code"); }}
                        className={`rounded-md px-2.5 py-1 text-xs font-medium transition ${
                          active
                            ? "bg-slate-950 text-white"
                            : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                        }`}
                      >
                        {item.label} ({item.size})
                      </button>
                    );
                  })}
                  {communityInfo.length > 30 && (
                    <span className="self-center text-xs text-slate-400">
                      +{communityInfo.length - 30} more
                    </span>
                  )}
                </div>
              </div>
            )}
          </section>

          <section className="flex items-center justify-between rounded-lg border border-slate-200 bg-white px-4 py-3">
            <div>
              <p className="text-sm font-semibold text-slate-900">{view === "overview" ? "Architecture overview" : "Code explorer"}</p>
              <p className="text-xs text-slate-500">{view === "overview" ? "Largest modules and the dependencies between them." : "Search or choose a module to inspect its code-level connections."}</p>
            </div>
            <div className="flex rounded-lg border border-slate-200 p-0.5 text-sm">
              {(["overview", "code"] as const).map((mode) => <button key={mode} onClick={() => setView(mode)} className={`rounded-md px-3 py-1.5 capitalize ${view === mode ? "bg-slate-950 text-white" : "text-slate-600 hover:bg-slate-100"}`}>{mode}</button>)}
            </div>
          </section>

          {view === "overview" ? (
            <div className="h-[640px]">
              <ClusterOverview
                communities={communityInfo}
                links={interCommunityLinks}
                onCommunityClick={focusCommunity}
                height={640}
              />
            </div>
          ) : (
            <div className="flex gap-4 h-[640px]">
              <div className="flex-1 min-w-0 h-full">
                <CodeGraph
                  data={filteredGraph}
                  height={640}
                  cooldownTicks={filteredGraph.nodes.length > 500 ? 200 : 120}
                  onNodeClick={(node) => setSelectedNode(node)}
                />
              </div>
              {selectedNode && (
                <div className="w-80 flex-shrink-0 flex flex-col border border-slate-700 rounded-lg overflow-hidden bg-slate-900 shadow-xl relative">
                  <button 
                    onClick={() => setSelectedNode(null)}
                    className="absolute top-4 right-4 z-10 text-slate-400 hover:text-white"
                  >
                    <X size={16} />
                  </button>
                  <div className="p-4 border-b border-slate-700 bg-slate-800 pr-10">
                    <h3 className="font-semibold text-slate-100 truncate" title={selectedNode.name || selectedNode.id}>
                      {selectedNode.name || selectedNode.id}
                    </h3>
                    <p className="text-xs text-slate-400 mt-1 capitalize">
                      {selectedNode.type || "Node"} • Community {selectedNode.community}
                    </p>
                  </div>
                  <div className="flex-1 min-h-0">
                    <CommentsPanel targetType="node" targetId={selectedNode.id} />
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

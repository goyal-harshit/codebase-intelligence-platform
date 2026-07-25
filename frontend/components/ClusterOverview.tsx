"use client";

import { useMemo } from "react";

interface CommunityInfo {
  id: number;
  label: string;
  size: number;
}

interface InterLink {
  source: number;
  target: number;
  weight: number;
}

interface ClusterOverviewProps {
  communities: CommunityInfo[];
  links: InterLink[];
  onCommunityClick: (communityId: number) => void;
  height?: number;
}

const COMMUNITY_COLORS = [
  "#6366f1", "#f43f5e", "#10b981", "#f59e0b", "#06b6d4",
  "#8b5cf6", "#ec4899", "#14b8a6", "#ef4444", "#84cc16",
  "#a855f7", "#0ea5e9", "#f97316", "#10b981", "#d946ef",
];

function communityColor(id: number): string {
  if (id < 0) return "#64748b";
  return COMMUNITY_COLORS[id % COMMUNITY_COLORS.length];
}

/**
 * A dedicated cluster overview visualization that renders community nodes
 * in a clean, non-overlapping circular layout with weighted inter-community
 * links and clear labels. Designed specifically for 4-30 community nodes.
 */
export default function ClusterOverview({
  communities,
  links,
  onCommunityClick,
  height = 640,
}: ClusterOverviewProps) {
  const width = 900; // SVG viewBox width — scales responsively via CSS

  // Compute node positions in a circle layout
  const layout = useMemo(() => {
    const n = communities.length;
    if (n === 0) return { nodes: [], edges: [] };

    const cx = width / 2;
    const cy = height / 2;
    // Radius of the circle on which nodes are placed
    const layoutRadius = Math.min(cx, cy) * 0.58;

    const nodes = communities.map((c, i) => {
      const angle = (2 * Math.PI * i) / n - Math.PI / 2; // Start from top
      const x = cx + layoutRadius * Math.cos(angle);
      const y = cy + layoutRadius * Math.sin(angle);
      const nodeRadius = Math.max(18, Math.min(40, 12 + Math.sqrt(c.size) * 4));
      return { ...c, x, y, radius: nodeRadius, angle };
    });

    // Build positioned edges
    const nodeMap = new Map(nodes.map((n) => [n.id, n]));
    const maxWeight = Math.max(1, ...links.map((l) => l.weight));

    const edges = links
      .map((l) => {
        const s = nodeMap.get(l.source);
        const t = nodeMap.get(l.target);
        if (!s || !t) return null;
        const thickness = Math.max(1, (l.weight / maxWeight) * 5);
        const opacity = Math.max(0.15, Math.min(0.6, l.weight / maxWeight));
        return { ...l, sx: s.x, sy: s.y, tx: t.x, ty: t.y, thickness, opacity };
      })
      .filter(Boolean) as Array<InterLink & { sx: number; sy: number; tx: number; ty: number; thickness: number; opacity: number }>;

    return { nodes, edges };
  }, [communities, links, width, height]);

  if (communities.length === 0) {
    return <p className="text-sm text-slate-500 p-4">No communities detected.</p>;
  }

  return (
    <div className="relative w-full rounded-lg border border-slate-200 bg-slate-950 overflow-hidden" style={{ height }}>
      {/* Navigation hint */}
      <div className="pointer-events-none absolute bottom-3 left-3 z-10 rounded-md bg-slate-900/85 px-3 py-1.5 text-[11px] text-slate-300 backdrop-blur border border-slate-800">
        Architecture Overview · Click any module to drill into its code-level graph
      </div>

      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full h-full"
        style={{ fontFamily: "'Inter', system-ui, sans-serif" }}
      >
        <defs>
          {/* Glow filter for nodes */}
          <filter id="node-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="6" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          {/* Arrow marker */}
          <marker
            id="cluster-arrow"
            viewBox="0 0 10 7"
            refX="10"
            refY="3.5"
            markerWidth="8"
            markerHeight="6"
            orient="auto"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="#818cf8" opacity="0.7" />
          </marker>
        </defs>

        {/* Inter-community edges */}
        {layout.edges.map((e, i) => {
          // Shorten line to stop at node perimeter
          const dx = e.tx - e.sx;
          const dy = e.ty - e.sy;
          const dist = Math.hypot(dx, dy) || 1;
          const sourceNode = layout.nodes.find((n) => n.id === e.source);
          const targetNode = layout.nodes.find((n) => n.id === e.target);
          const sr = sourceNode?.radius || 20;
          const tr = targetNode?.radius || 20;
          const x1 = e.sx + (dx / dist) * (sr + 4);
          const y1 = e.sy + (dy / dist) * (sr + 4);
          const x2 = e.tx - (dx / dist) * (tr + 12);
          const y2 = e.ty - (dy / dist) * (tr + 12);

          return (
            <line
              key={i}
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke="#818cf8"
              strokeWidth={e.thickness}
              opacity={e.opacity}
              markerEnd="url(#cluster-arrow)"
              strokeLinecap="round"
            />
          );
        })}

        {/* Community nodes + labels */}
        {layout.nodes.map((node) => {
          const color = communityColor(node.id);
          // Compute label position — outside the circle, pointing outward
          const cx = width / 2;
          const cy = height / 2;
          const dx = node.x - cx;
          const dy = node.y - cy;
          const dist = Math.hypot(dx, dy) || 1;
          const labelOffset = node.radius + 16;
          const labelX = node.x + (dx / dist) * labelOffset;
          const labelY = node.y + (dy / dist) * labelOffset;
          const textAnchor = dx >= 0 ? "start" : "end";

          return (
            <g
              key={node.id}
              onClick={() => onCommunityClick(node.id)}
              className="cursor-pointer"
              role="button"
              tabIndex={0}
            >
              {/* Outer glow ring */}
              <circle
                cx={node.x}
                cy={node.y}
                r={node.radius + 5}
                fill={color}
                opacity={0.15}
              />
              {/* Main node circle */}
              <circle
                cx={node.x}
                cy={node.y}
                r={node.radius}
                fill={color}
                opacity={0.9}
                stroke="rgba(255,255,255,0.35)"
                strokeWidth={1.5}
                filter="url(#node-glow)"
              />
              {/* File count inside node */}
              <text
                x={node.x}
                y={node.y + 1}
                textAnchor="middle"
                dominantBaseline="central"
                fill="white"
                fontSize={Math.min(14, node.radius * 0.55)}
                fontWeight={700}
                opacity={0.95}
              >
                {node.size}
              </text>

              {/* Label pill positioned OUTSIDE the node circle */}
              <rect
                x={textAnchor === "start" ? labelX - 6 : labelX - (node.label.length * 7.5) - 6}
                y={labelY - 12}
                width={node.label.length * 7.5 + 12}
                height={24}
                rx={6}
                fill="rgba(15, 23, 42, 0.92)"
                stroke="rgba(255, 255, 255, 0.2)"
                strokeWidth={0.8}
              />
              <text
                x={labelX}
                y={labelY + 1}
                textAnchor={textAnchor}
                dominantBaseline="central"
                fill="white"
                fontSize={13}
                fontWeight={600}
              >
                {node.label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

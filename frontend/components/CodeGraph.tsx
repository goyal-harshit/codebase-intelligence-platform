"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
});

export interface GraphData {
  nodes: { id: string; name: string; type?: string; community?: number }[];
  links: { source: string | any; target: string | any }[];
}

/* Deterministic palette for community colors */
const COMMUNITY_COLORS = [
  "#6366f1", "#f43f5e", "#10b981", "#f59e0b", "#3b82f6",
  "#8b5cf6", "#ec4899", "#14b8a6", "#ef4444", "#22c55e",
  "#a855f7", "#06b6d4", "#f97316", "#84cc16", "#e879f9",
  "#0ea5e9", "#d946ef", "#fb923c", "#4ade80", "#fbbf24",
];

function communityColor(community?: number): string {
  if (community === undefined || community < 0) return "#94a3b8";
  return COMMUNITY_COLORS[community % COMMUNITY_COLORS.length];
}

interface CodeGraphProps {
  data: GraphData;
  height?: number;
  /** Stop simulation after N ticks (default 120). Prevents infinite CPU usage. */
  cooldownTicks?: number;
  onNodeClick?: (node: any) => void;
}

export default function CodeGraph({
  data,
  height = 520,
  cooldownTicks = 120,
  onNodeClick,
}: CodeGraphProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [width, setWidth] = useState(760);

  useEffect(() => {
    if (!ref.current) return;
    const resize = () =>
      setWidth(Math.max(320, ref.current?.clientWidth ?? 760));
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  // Compute node degree to size nodes based on their importance
  const nodeDegree = useMemo(() => {
    const degree = new Map<string, number>();
    data.links.forEach((l) => {
      const s = typeof l.source === "object" ? l.source.id : l.source;
      const t = typeof l.target === "object" ? l.target.id : l.target;
      degree.set(s, (degree.get(s) || 0) + 1);
      degree.set(t, (degree.get(t) || 0) + 1);
    });
    return degree;
  }, [data]);

  const nodeCanvasObject = useCallback(
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const label = node.name || node.id;
      const degree = nodeDegree.get(node.id) || 1;
      const baseR = Math.max(2, Math.sqrt(degree) * 1.5);
      const r = baseR + (1 / globalScale); // Maintain visibility when zoomed out

      // Node circle
      ctx.beginPath();
      ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
      ctx.fillStyle = communityColor(node.community);
      ctx.fill();

      // Node border
      ctx.lineWidth = 0.5 / globalScale;
      ctx.strokeStyle = "#ffffff";
      ctx.stroke();

      // Label (only at sufficient zoom, or for very important nodes)
      if (globalScale > 1.2 || (degree > 10 && globalScale > 0.6)) {
        const fontSize = Math.min(12 / globalScale, 5);
        ctx.font = `${fontSize}px Inter, sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        
        // Label background for readability
        const textWidth = ctx.measureText(label).width;
        const bgHeight = fontSize * 1.2;
        ctx.fillStyle = "rgba(255, 255, 255, 0.7)";
        ctx.fillRect(node.x - textWidth / 2 - 1, node.y + r + 0.5, textWidth + 2, bgHeight);
        
        ctx.fillStyle = "#1e293b";
        ctx.fillText(label, node.x, node.y + r + 1);
      }
    },
    [nodeDegree],
  );

  if (data.nodes.length === 0)
    return (
      <p className="text-sm text-slate-500">Nothing to visualize yet.</p>
    );

  return (
    <div
      ref={ref}
      className="overflow-hidden rounded-lg border border-slate-200 bg-white"
    >
      <ForceGraph2D
        graphData={data}
        nodeLabel="name"
        nodeAutoColorBy="type"
        nodeCanvasObject={nodeCanvasObject}
        nodePointerAreaPaint={(node: any, color, ctx) => {
          const degree = nodeDegree.get(node.id) || 1;
          const r = Math.max(2, Math.sqrt(degree) * 1.5) + 3;
          ctx.beginPath();
          ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
          ctx.fillStyle = color;
          ctx.fill();
        }}
        linkDirectionalArrowLength={3.5}
        linkDirectionalArrowRelPos={1}
        linkColor={() => "rgba(203, 213, 225, 0.6)"} // slate-300 with opacity
        linkWidth={0.8}
        height={height}
        width={width}
        cooldownTicks={cooldownTicks}
        warmupTicks={30}
        d3AlphaDecay={0.03}
        d3VelocityDecay={0.4}
        enableNodeDrag={true}
        enableZoomInteraction={true}
        onNodeClick={onNodeClick}
      />
    </div>
  );
}

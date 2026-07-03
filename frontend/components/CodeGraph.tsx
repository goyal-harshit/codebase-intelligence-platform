"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import SpriteText from "three-spritetext";

// next/dynamic's wrapper cannot forward refs, and we need the 3D instance for
// camera flights — smuggle the ref through as a regular prop instead.
const ForceGraph3D = dynamic(
  async () => {
    const { default: FG } = await import("react-force-graph-3d");
    const Wrapper = ({ fgRef, ...props }: any) => <FG {...props} ref={fgRef} />;
    Wrapper.displayName = "ForceGraph3DWrapper";
    return Wrapper;
  },
  { ssr: false },
);
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
});

export interface GraphData {
  nodes: { id: string; name: string; type?: string; community?: number }[];
  links: { source: string | any; target: string | any }[];
}

/* Deterministic palette for community colors */
const COMMUNITY_COLORS = [
  "#818cf8", "#fb7185", "#34d399", "#fbbf24", "#60a5fa",
  "#a78bfa", "#f472b6", "#2dd4bf", "#f87171", "#4ade80",
  "#c084fc", "#22d3ee", "#fb923c", "#a3e635", "#e879f9",
  "#38bdf8", "#e0aaff", "#fdba74", "#86efac", "#fde047",
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
  const fg3dRef = useRef<any>(null);
  const didInitialFit = useRef(false);
  const didTuneForces = useRef(false);
  const [width, setWidth] = useState(760);
  const [mode, setMode] = useState<"3d" | "2d">("3d");

  useEffect(() => {
    if (!ref.current) return;
    const resize = () =>
      setWidth(Math.max(320, ref.current?.clientWidth ?? 760));
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  // New data -> re-tune forces and re-frame the view once it settles.
  useEffect(() => {
    didInitialFit.current = false;
    didTuneForces.current = false;
  }, [data]);

  /* Spread communities further apart than the d3 defaults — the extra spacing
     is what makes labels readable and clusters distinguishable in 3D. */
  const tuneForces = useCallback(() => {
    const fg = fg3dRef.current;
    if (!fg) return;
    fg.d3Force("charge")?.strength(-90);
    fg.d3Force("link")?.distance(45);
  }, []);

  const fitView = useCallback((ms = 800) => {
    fg3dRef.current?.zoomToFit(ms, 60);
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

  /* Label hubs persistently; small graphs get labels everywhere. Everything
     else still shows its name on hover via nodeLabel. Sprites are capped —
     each one is a texture, and hundreds of them are what makes 3D crawl. */
  const labelThreshold = useMemo(() => {
    if (data.nodes.length <= 150) return 0;
    if (data.nodes.length <= 500) return 5;
    return 10;
  }, [data.nodes.length]);

  const nodeThreeObject = useCallback(
    (node: any) => {
      const degree = nodeDegree.get(node.id) || 1;
      if (degree < labelThreshold) return undefined as any; // sphere only
      const sprite = new SpriteText(node.name || node.id);
      sprite.color = "#f1f5f9";
      sprite.backgroundColor = "rgba(15, 23, 42, 0.7)";
      sprite.padding = 2;
      sprite.borderRadius = 2;
      sprite.fontWeight = "600";
      sprite.textHeight = Math.min(5 + Math.sqrt(degree) * 0.7, 10);
      // Float the label above the sphere so it never hides the node.
      (sprite as any).position.y = Math.max(6, Math.sqrt(degree) * 1.8 + 4);
      return sprite;
    },
    [nodeDegree, labelThreshold],
  );

  /* Fly the camera to the clicked node, then bubble the click up. */
  const handle3DNodeClick = useCallback(
    (node: any) => {
      const fg = fg3dRef.current;
      if (fg && Number.isFinite(node.x)) {
        const distance = 90;
        const len = Math.hypot(node.x, node.y, node.z) || 1;
        const ratio = 1 + distance / len;
        fg.cameraPosition(
          { x: node.x * ratio, y: node.y * ratio, z: node.z * ratio },
          node,
          1200,
        );
      }
      onNodeClick?.(node);
    },
    [onNodeClick],
  );

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
      className="relative overflow-hidden rounded-lg border border-slate-200 bg-white"
      style={{ height }}
    >
      {/* Controls: reset view + mode toggle */}
      <div className="absolute right-3 top-3 z-10 flex items-center gap-2">
        {mode === "3d" && (
          <button
            onClick={() => fitView()}
            className="rounded-lg border border-slate-600/40 bg-slate-900/70 px-3 py-1.5 text-xs font-medium text-slate-300 backdrop-blur transition hover:bg-slate-700/60"
          >
            Reset view
          </button>
        )}
        <div className="flex overflow-hidden rounded-lg border border-slate-600/40 bg-slate-900/70 text-xs font-medium backdrop-blur">
          {(["3d", "2d"] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`px-3 py-1.5 uppercase transition ${
                mode === m
                  ? "bg-indigo-500 text-white"
                  : "text-slate-300 hover:bg-slate-700/60"
              }`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      {/* Navigation hint */}
      {mode === "3d" && (
        <div className="pointer-events-none absolute bottom-3 left-3 z-10 rounded-md bg-slate-900/70 px-2.5 py-1.5 text-[11px] text-slate-400 backdrop-blur">
          drag: rotate · scroll: zoom · right-drag: pan · click node: focus
        </div>
      )}

      {mode === "3d" ? (
        <ForceGraph3D
          fgRef={fg3dRef}
          graphData={data}
          width={width}
          height={height}
          backgroundColor="#0f172a"
          controlType="orbit"
          rendererConfig={{ antialias: false, powerPreference: "high-performance" }}
          nodeLabel={(n: any) =>
            `${n.name || n.id}${n.type ? ` · ${n.type}` : ""} · C${n.community ?? "?"}`
          }
          nodeColor={(n: any) => communityColor(n.community)}
          nodeVal={(n: any) => Math.max(1, (nodeDegree.get(n.id) || 1) * 0.8)}
          nodeOpacity={0.92}
          nodeResolution={8}
          nodeThreeObject={nodeThreeObject}
          nodeThreeObjectExtend={true}
          linkColor={() => "rgba(148, 163, 184, 0.4)"}
          linkOpacity={0.3}
          /* linkWidth 0 keeps links as GL lines; any width>0 turns each of the
             ~2.6k links into a cylinder mesh and tanks the frame rate. Same
             reason there are no directional arrows in 3D (2.6k cone meshes). */
          linkWidth={0}
          linkDirectionalParticles={0}
          cooldownTicks={cooldownTicks}
          warmupTicks={60}
          onEngineTick={() => {
            if (!didTuneForces.current) {
              didTuneForces.current = true;
              tuneForces();
            }
          }}
          onEngineStop={() => {
            if (!didInitialFit.current) {
              didInitialFit.current = true;
              fitView(600);
            }
          }}
          enableNodeDrag={false}
          enableNavigationControls={true}
          showNavInfo={false}
          onNodeClick={handle3DNodeClick}
        />
      ) : (
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
      )}
    </div>
  );
}

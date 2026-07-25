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
  nodes: { id: string; name: string; type?: string; community?: number; size?: number }[];
  links: { source: string | any; target: string | any; weight?: number }[];
}

/* Deterministic vibrant palette for community colors */
const COMMUNITY_COLORS = [
  "#6366f1", "#f43f5e", "#10b981", "#f59e0b", "#06b6d4",
  "#8b5cf6", "#ec4899", "#14b8a6", "#ef4444", "#84cc16",
  "#a855f7", "#0ea5e9", "#f97316", "#10b981", "#d946ef",
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
  cooldownTicks = 180,
  onNodeClick,
}: CodeGraphProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  const fg3dRef = useRef<any>(null);
  const fg2dRef = useRef<any>(null);
  const didInitialFit = useRef(false);
  const didTuneForces = useRef(false);
  const [width, setWidth] = useState(760);
  const [mode, setMode] = useState<"3d" | "2d">("2d");

  useEffect(() => {
    if (!ref.current) return;
    const resize = () =>
      setWidth(Math.max(320, ref.current?.clientWidth ?? 760));
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  /* Tune 2D forces for wide, un-cluttered cluster spacing */
  useEffect(() => {
    const fg2d = fg2dRef.current;
    if (fg2d && mode === "2d") {
      fg2d.d3Force("charge")?.strength(-480);
      fg2d.d3Force("link")?.distance(130);
    }
  }, [data, mode]);

  // New data -> re-tune forces and re-frame the view once it settles.
  useEffect(() => {
    didInitialFit.current = false;
    didTuneForces.current = false;
  }, [data]);

  /* Tune 3D forces for spacious layout distribution across the viewport */
  const tuneForces = useCallback(() => {
    const fg = fg3dRef.current;
    if (!fg) return;
    fg.d3Force("charge")?.strength(-420);
    fg.d3Force("link")?.distance(130);
  }, []);

  const fitView = useCallback((ms = 800) => {
    fg3dRef.current?.zoomToFit(ms, 40);
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

  const labelThreshold = useMemo(() => {
    if (data.nodes.length <= 150) return 0;
    if (data.nodes.length <= 500) return 3;
    return 8;
  }, [data.nodes.length]);

  /* Billboarded 3D text sprites with rounded dark background pills for 360° legibility */
  const nodeThreeObject = useCallback(
    (node: any) => {
      const degree = nodeDegree.get(node.id) || 1;
      if (degree < labelThreshold) return undefined as any;

      const sprite = new SpriteText(node.name || node.id);
      sprite.color = "#ffffff";
      sprite.backgroundColor = "rgba(15, 23, 42, 0.85)";
      sprite.padding = [2, 4];
      sprite.borderRadius = 3;
      sprite.borderWidth = 0.5;
      sprite.borderColor = "rgba(255, 255, 255, 0.25)";
      sprite.fontWeight = "600";
      sprite.fontFace = "Inter, sans-serif";
      sprite.textHeight = Math.min(4.5 + Math.sqrt(degree) * 0.6, 9);

      // Offset label above the node sphere
      const baseR = Math.max(3, Math.sqrt(degree) * 1.2);
      (sprite as any).position.y = baseR + (sprite.textHeight / 2) + 2.5;

      const mat = (sprite as any).material;
      if (mat) {
        mat.depthTest = true;
        mat.depthWrite = false;
        (sprite as any).renderOrder = 999;
      }
      return sprite;
    },
    [nodeDegree, labelThreshold],
  );

  /* Fly the camera to the clicked node */
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

  /* 2D Canvas rendering with crisp nodes, directional flow, and pill labels */
  const nodeCanvasObject = useCallback(
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const label = node.name || node.id;
      const degree = nodeDegree.get(node.id) || 1;
      const r = Math.max(3.5, Math.sqrt(degree) * 1.6) + (1 / globalScale);

      // Outer glowing halo
      ctx.beginPath();
      ctx.arc(node.x, node.y, r + 2 / globalScale, 0, 2 * Math.PI);
      ctx.fillStyle = communityColor(node.community);
      ctx.globalAlpha = 0.25;
      ctx.fill();
      ctx.globalAlpha = 1.0;

      // Node circle
      ctx.beginPath();
      ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
      ctx.fillStyle = communityColor(node.community);
      ctx.fill();

      // Node crisp border
      ctx.lineWidth = 1 / globalScale;
      ctx.strokeStyle = "#ffffff";
      ctx.stroke();

      // Readable label pill
      if (globalScale > 0.7 || (degree > 4 && globalScale > 0.35)) {
        const fontSize = Math.max(9 / globalScale, 3);
        ctx.font = `600 ${fontSize}px Inter, sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";

        const textWidth = ctx.measureText(label).width;
        const paddingX = 4 / globalScale;
        const paddingY = 2 / globalScale;
        const labelY = node.y + r + (fontSize / 2) + (3 / globalScale);

        ctx.fillStyle = "rgba(15, 23, 42, 0.85)";
        ctx.strokeStyle = "rgba(255, 255, 255, 0.25)";
        ctx.lineWidth = 0.5 / globalScale;

        const rectX = node.x - textWidth / 2 - paddingX;
        const rectY = labelY - fontSize / 2 - paddingY;
        const rectW = textWidth + paddingX * 2;
        const rectH = fontSize + paddingY * 2;

        ctx.beginPath();
        if (typeof (ctx as any).roundRect === "function") {
          (ctx as any).roundRect(rectX, rectY, rectW, rectH, 3 / globalScale);
        } else {
          ctx.rect(rectX, rectY, rectW, rectH);
        }
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = "#ffffff";
        ctx.fillText(label, node.x, labelY);
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
      className="relative overflow-hidden rounded-lg border border-slate-200 bg-slate-950"
      style={{ height }}
    >
      {/* Controls: reset view + mode toggle */}
      <div className="absolute right-3 top-3 z-10 flex items-center gap-2">
        {mode === "3d" && (
          <button
            onClick={() => fitView()}
            className="rounded-lg border border-slate-600/40 bg-slate-900/80 px-3 py-1.5 text-xs font-medium text-slate-300 backdrop-blur transition hover:bg-slate-700/60"
          >
            Reset view
          </button>
        )}
        <div className="flex overflow-hidden rounded-lg border border-slate-600/40 bg-slate-900/80 text-xs font-medium backdrop-blur">
          {(["3d", "2d"] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`px-3 py-1.5 uppercase transition ${
                mode === m
                  ? "bg-indigo-600 text-white"
                  : "text-slate-300 hover:bg-slate-700/60"
              }`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      {/* Navigation hint */}
      <div className="pointer-events-none absolute bottom-3 left-3 z-10 rounded-md bg-slate-900/80 px-3 py-1.5 text-[11px] text-slate-300 backdrop-blur border border-slate-800">
        {mode === "3d"
          ? "3D View · Drag to rotate · Scroll to zoom · Right-drag to pan · Animated flow particles show direction"
          : "2D View · Drag to pan · Scroll to zoom · Click node to inspect details · Directional arrows show dependency flow"}
      </div>

      {mode === "3d" ? (
        <ForceGraph3D
          fgRef={fg3dRef}
          graphData={data}
          width={width}
          height={height}
          backgroundColor="#090d16"
          controlType="orbit"
          rendererConfig={{ antialias: true, powerPreference: "high-performance" }}
          nodeLabel={(n: any) =>
            `${n.name || n.id}${n.type ? ` · ${n.type}` : ""} · Community ${n.community ?? "?"}`
          }
          nodeColor={(n: any) => communityColor(n.community)}
          nodeVal={(n: any) => Math.max(3, n.size || (nodeDegree.get(n.id) || 1) * 1.5)}
          nodeOpacity={0.95}
          nodeResolution={16}
          nodeThreeObject={nodeThreeObject}
          nodeThreeObjectExtend={true}
          /* Directional arrows & animated flow particles in 3D */
          linkDirectionalArrowLength={4.5}
          linkDirectionalArrowRelPos={0.88}
          linkDirectionalArrowColor={() => "#818cf8"}
          linkDirectionalParticles={2}
          linkDirectionalParticleSpeed={0.006}
          linkDirectionalParticleWidth={1.5}
          linkDirectionalParticleColor={() => "#c084fc"}
          linkColor={() => "rgba(148, 163, 184, 0.35)"}
          linkOpacity={0.4}
          linkWidth={0.8}
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
          ref={fg2dRef}
          graphData={data}
          nodeLabel="name"
          nodeAutoColorBy="type"
          nodeCanvasObject={nodeCanvasObject}
          nodePointerAreaPaint={(node: any, color, ctx) => {
            const degree = nodeDegree.get(node.id) || 1;
            const r = Math.max(3.5, Math.sqrt(degree) * 1.6) + 3;
            ctx.beginPath();
            ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
            ctx.fillStyle = color;
            ctx.fill();
          }}
          /* Directional arrows & animated flow particles in 2D */
          linkDirectionalArrowLength={5}
          linkDirectionalArrowRelPos={0.88}
          linkDirectionalArrowColor={() => "#6366f1"}
          linkDirectionalParticles={2}
          linkDirectionalParticleSpeed={0.006}
          linkDirectionalParticleWidth={2}
          linkDirectionalParticleColor={() => "#818cf8"}
          linkColor={() => "rgba(148, 163, 184, 0.45)"}
          linkWidth={1.2}
          height={height}
          width={width}
          cooldownTicks={cooldownTicks}
          warmupTicks={30}
          d3AlphaDecay={0.015}
          d3VelocityDecay={0.3}
          enableNodeDrag={true}
          enableZoomInteraction={true}
          onNodeClick={onNodeClick}
        />
      )}
    </div>
  );
}

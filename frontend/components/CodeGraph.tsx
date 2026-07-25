"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
// @ts-ignore
import * as THREE from "three";
import SpriteText from "three-spritetext";

const ForceGraph3D = dynamic(
  async () => {
    const { default: FG } = await import("react-force-graph-3d");
    const Wrapper = ({ fgRef, ...props }: any) => <FG {...props} ref={fgRef} />;
    Wrapper.displayName = "ForceGraph3DWrapper";
    return Wrapper;
  },
  { ssr: false },
);

const ForceGraph2D = dynamic(
  async () => {
    const { default: FG } = await import("react-force-graph-2d");
    const Wrapper = ({ fgRef, ...props }: any) => <FG {...props} ref={fgRef} />;
    Wrapper.displayName = "ForceGraph2DWrapper";
    return Wrapper;
  },
  { ssr: false },
);

export interface GraphData {
  nodes: { id: string; name: string; type?: string; community?: number; size?: number; file?: string }[];
  links: { source: string | any; target: string | any; weight?: number }[];
}

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
  cooldownTicks?: number;
  onNodeClick?: (node: any) => void;
}

export default function CodeGraph({
  data,
  height = 580,
  cooldownTicks = 200,
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

  const nodeCount = Math.max(1, data.nodes.length);

  /*
   * GENTLE force tuning — keep the graph compact and readable.
   * The key insight: charge should be just strong enough to separate
   * nodes, but not so strong that they fly to the edges of the viewport.
   * For ~50 nodes: charge ~ -80, linkDist ~ 50
   * For ~200 nodes: charge ~ -60, linkDist ~ 40
   * For ~500+ nodes: charge ~ -40, linkDist ~ 30
   */
  const dynamicCharge = useMemo(() => {
    if (nodeCount <= 20) return -120;
    if (nodeCount <= 80) return -90;
    if (nodeCount <= 200) return -65;
    return -45;
  }, [nodeCount]);

  const dynamicDistance = useMemo(() => {
    if (nodeCount <= 20) return 70;
    if (nodeCount <= 80) return 55;
    if (nodeCount <= 200) return 40;
    return 30;
  }, [nodeCount]);

  /* Node visual radius: degree-scaled but reasonable.
   * Small nodes = 4, hub nodes = up to 10. Never invisible, never giant. */
  const nodeRadius = useCallback(
    (nodeId: string) => {
      const degree = nodeDegree.get(nodeId) || 1;
      return Math.min(10, Math.max(4, 3.5 + Math.sqrt(degree) * 1.1));
    },
    [nodeDegree],
  );

  // Apply forces to 2D graph — including center gravity for disconnected clusters
  useEffect(() => {
    const fg = fg2dRef.current;
    if (!fg || mode !== "2d") return;
    fg.d3Force("charge")?.strength(dynamicCharge);
    fg.d3Force("link")?.distance(dynamicDistance);

    // Gravity: pull ALL nodes toward center so disconnected clusters
    // don't drift to corners. Use the force graph's internal d3 module.
    // forceX/forceY with strength 0.12 = gentle but effective centering.
    const d3f = (fg as any).d3Force;
    if (d3f) {
      // The force graph instance exposes d3 forces.
      // We create simple centering forces manually.
      const gravityForce = (axis: "x" | "y") => {
        const strength = 0.12;
        return (alpha: number) => {
          const nodes = fg.graphData().nodes;
          nodes.forEach((node: any) => {
            const v = axis === "x" ? "vx" : "vy";
            node[v] = (node[v] || 0) + (0 - (node[axis] || 0)) * strength * alpha;
          });
        };
      };
      fg.d3Force("gravityX", gravityForce("x"));
      fg.d3Force("gravityY", gravityForce("y"));
    }
  }, [data, mode, dynamicCharge, dynamicDistance]);

  // Apply forces to 3D graph
  const tuneForces = useCallback(() => {
    const fg = fg3dRef.current;
    if (!fg) return;
    fg.d3Force("charge")?.strength(dynamicCharge * 1.5);
    fg.d3Force("link")?.distance(dynamicDistance * 1.8);

    // 3D gravity toward origin
    const gravity3D = (axis: "x" | "y" | "z") => {
      const strength = 0.1;
      return (alpha: number) => {
        const nodes = fg.graphData().nodes;
        nodes.forEach((node: any) => {
          const v = `v${axis}`;
          node[v] = (node[v] || 0) + (0 - (node[axis] || 0)) * strength * alpha;
        });
      };
    };
    fg.d3Force("gravityX", gravity3D("x"));
    fg.d3Force("gravityY", gravity3D("y"));
    fg.d3Force("gravityZ", gravity3D("z"));
  }, [dynamicCharge, dynamicDistance]);

  useEffect(() => {
    didInitialFit.current = false;
    didTuneForces.current = false;
  }, [data]);

  const fitView = useCallback((ms = 800) => {
    fg3dRef.current?.zoomToFit(ms, 50);
  }, []);

  /* ──────────────────────────────────────────────
     3D: Custom THREE.Group — sphere + billboard text ABOVE
     ────────────────────────────────────────────── */
  const nodeThreeObject = useCallback(
    (node: any) => {
      const group = new THREE.Group();
      const r = nodeRadius(node.id);

      // Sphere
      const geometry = new THREE.SphereGeometry(r, 16, 16);
      const material = new THREE.MeshLambertMaterial({
        color: communityColor(node.community),
        transparent: true,
        opacity: 0.92,
      });
      group.add(new THREE.Mesh(geometry, material));

      // Billboard text ABOVE sphere
      const sprite = new SpriteText(node.name || node.id);
      sprite.color = "#ffffff";
      sprite.backgroundColor = "rgba(15, 23, 42, 0.88)";
      sprite.padding = [1.5, 4];
      sprite.borderRadius = 3;
      sprite.borderWidth = 0.4;
      sprite.borderColor = "rgba(255, 255, 255, 0.25)";
      sprite.fontWeight = "600";
      sprite.fontFace = "Inter, sans-serif";
      sprite.textHeight = 3.5;
      (sprite as any).position.y = r + 5;

      const mat = (sprite as any).material;
      if (mat) {
        mat.depthTest = false;
        mat.depthWrite = false;
        (sprite as any).renderOrder = 999;
      }
      group.add(sprite);
      return group;
    },
    [nodeRadius],
  );

  /* ──────────────────────────────────────────────
     2D: Canvas rendering — visible nodes + always-on labels
     ────────────────────────────────────────────── */
  const nodeCanvasObject = useCallback(
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const label = node.name || node.id;
      const degree = nodeDegree.get(node.id) || 1;
      const r = nodeRadius(node.id);

      // 1. Subtle glow halo
      ctx.beginPath();
      ctx.arc(node.x, node.y, r + 2, 0, 2 * Math.PI);
      ctx.fillStyle = communityColor(node.community);
      ctx.globalAlpha = 0.2;
      ctx.fill();
      ctx.globalAlpha = 1.0;

      // 2. Solid node circle
      ctx.beginPath();
      ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
      ctx.fillStyle = communityColor(node.community);
      ctx.fill();
      ctx.lineWidth = 0.8 / globalScale;
      ctx.strokeStyle = "rgba(255,255,255,0.5)";
      ctx.stroke();

      // 3. Label — ALWAYS visible for small/medium graphs.
      //    For massive graphs (500+), hide low-degree labels when zoomed out.
      const showLabel =
        nodeCount <= 100 ||
        globalScale >= 0.6 ||
        (degree >= 4 && globalScale >= 0.3);

      if (showLabel) {
        // Font targets ~8px on screen. screenPx = worldUnits * globalScale.
        // worldUnits = 8 / globalScale. Cap at 4.5 world units when zoomed in.
        const fontSize = Math.min(4.5, 8 / globalScale);
        ctx.font = `600 ${fontSize}px Inter, sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "top";

        const textWidth = ctx.measureText(label).width;
        const px = 3 / globalScale;
        const py = 1.5 / globalScale;
        const gap = 2.5 / globalScale;

        // Pill positioned BELOW node circle
        const pillY = node.y + r + gap;
        const pillW = textWidth + px * 2;
        const pillH = fontSize + py * 2;
        const pillX = node.x - pillW / 2;

        // Dark pill background
        ctx.fillStyle = "rgba(15, 23, 42, 0.88)";
        ctx.strokeStyle = "rgba(255,255,255,0.2)";
        ctx.lineWidth = 0.4 / globalScale;
        ctx.beginPath();
        if (typeof (ctx as any).roundRect === "function") {
          (ctx as any).roundRect(pillX, pillY, pillW, pillH, 2.5 / globalScale);
        } else {
          ctx.rect(pillX, pillY, pillW, pillH);
        }
        ctx.fill();
        ctx.stroke();

        // White text
        ctx.fillStyle = "#ffffff";
        ctx.fillText(label, node.x, pillY + py);
      }
    },
    [nodeDegree, nodeRadius, nodeCount],
  );

  if (data.nodes.length === 0)
    return <p className="text-sm text-slate-500">Nothing to visualize yet.</p>;

  return (
    <div
      ref={ref}
      className="relative overflow-hidden rounded-lg border border-slate-200 bg-slate-950 shadow-inner"
      style={{ height }}
    >
      {/* Controls */}
      <div className="absolute right-3 top-3 z-10 flex items-center gap-2">
        <button
          onClick={() => {
            if (mode === "3d") {
              fitView();
            } else {
              fg2dRef.current?.zoomToFit(400, 40);
            }
          }}
          className="rounded-lg border border-slate-600/40 bg-slate-900/80 px-3 py-1.5 text-xs font-medium text-slate-300 backdrop-blur transition hover:bg-slate-700/60"
        >
          Reset view
        </button>
        <div className="flex overflow-hidden rounded-lg border border-slate-600/40 bg-slate-900/80 text-xs font-medium backdrop-blur">
          {(["3d", "2d"] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`px-3 py-1.5 uppercase transition ${
                mode === m
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-300 hover:bg-slate-700/60"
              }`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      {/* Hint */}
      <div className="pointer-events-none absolute bottom-3 left-3 z-10 rounded-md bg-slate-900/85 px-3 py-1.5 text-[11px] text-slate-300 backdrop-blur border border-slate-800">
        {mode === "3d"
          ? "3D · Drag rotate · Scroll zoom · Labels always face camera"
          : "2D · Scroll zoom · Drag pan · Click node to inspect · Arrows = dependency flow"}
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
            `${n.name || n.id}${n.type ? ` · ${n.type}` : ""} · C${n.community ?? "?"}`
          }
          nodeThreeObject={nodeThreeObject}
          nodeThreeObjectExtend={false}
          nodeVal={() => 0.01}
          linkDirectionalArrowLength={4}
          linkDirectionalArrowRelPos={0.88}
          linkDirectionalArrowColor={() => "#818cf8"}
          linkDirectionalParticles={2}
          linkDirectionalParticleSpeed={0.005}
          linkDirectionalParticleWidth={1.2}
          linkDirectionalParticleColor={() => "#c084fc"}
          linkColor={() => "rgba(148, 163, 184, 0.3)"}
          linkOpacity={0.35}
          linkWidth={0.6}
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
          onNodeClick={onNodeClick}
        />
      ) : (
        <ForceGraph2D
          fgRef={fg2dRef}
          graphData={data}
          nodeLabel="name"
          nodeAutoColorBy="type"
          nodeCanvasObject={nodeCanvasObject}
          nodePointerAreaPaint={(node: any, color, ctx) => {
            const r = nodeRadius(node.id) + 2;
            ctx.beginPath();
            ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
            ctx.fillStyle = color;
            ctx.fill();
          }}
          linkDirectionalArrowLength={4.5}
          linkDirectionalArrowRelPos={0.88}
          linkDirectionalArrowColor={() => "#6366f1"}
          linkDirectionalParticles={2}
          linkDirectionalParticleSpeed={0.005}
          linkDirectionalParticleWidth={1.5}
          linkDirectionalParticleColor={() => "#818cf8"}
          linkColor={() => "rgba(148, 163, 184, 0.4)"}
          linkWidth={1}
          height={height}
          width={width}
          cooldownTicks={cooldownTicks}
          warmupTicks={40}
          d3AlphaDecay={0.02}
          d3VelocityDecay={0.35}
          enableNodeDrag={true}
          enableZoomInteraction={true}
          onNodeClick={onNodeClick}
          onEngineStop={() => {
            // Auto-fit the 2D view once the layout settles
            fg2dRef.current?.zoomToFit(400, 50);
          }}
        />
      )}
    </div>
  );
}

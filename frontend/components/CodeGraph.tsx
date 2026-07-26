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
   * Gentle force tuning for spacious, readable layout.
   */
  const dynamicCharge = useMemo(() => {
    if (nodeCount <= 20) return -180;
    if (nodeCount <= 80) return -140;
    if (nodeCount <= 200) return -100;
    if (nodeCount <= 400) return -80;
    return -60;
  }, [nodeCount]);

  const dynamicDistance = useMemo(() => {
    if (nodeCount <= 20) return 80;
    if (nodeCount <= 80) return 65;
    if (nodeCount <= 200) return 50;
    if (nodeCount <= 400) return 40;
    return 35;
  }, [nodeCount]);

  /* Node visual radius: degree-scaled but reasonable. */
  const nodeRadius = useCallback(
    (nodeId: string) => {
      const degree = nodeDegree.get(nodeId) || 1;
      return Math.min(10, Math.max(4, 3.5 + Math.sqrt(degree) * 1.1));
    },
    [nodeDegree],
  );

  // Apply forces to 2D graph — including collision force (NO OVERLAP) & gentle gravity
  useEffect(() => {
    const fg = fg2dRef.current;
    if (!fg || mode !== "2d") return;
    fg.d3Force("charge")?.strength(dynamicCharge);
    fg.d3Force("link")?.distance(dynamicDistance);

    // 1. Collision Force: Hard physical boundary around every node & label to prevent overlap
    const collideForce = (alpha: number) => {
      const gData = fg.graphData();
      if (!gData || !gData.nodes) return;
      const nodes = gData.nodes;
      const n = nodes.length;
      for (let i = 0; i < n; i++) {
        const a = nodes[i];
        if (!Number.isFinite(a.x) || !Number.isFinite(a.y)) continue;
        const ra = nodeRadius(a.id) + 14;
        for (let j = i + 1; j < n; j++) {
          const b = nodes[j];
          if (!Number.isFinite(b.x) || !Number.isFinite(b.y)) continue;
          const rb = nodeRadius(b.id) + 14;
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const dist = Math.hypot(dx, dy) || 0.1;
          const minDist = ra + rb;
          if (dist < minDist) {
            const overlap = ((minDist - dist) / dist) * 0.4 * alpha;
            if (a.fx == null) {
              a.x -= dx * overlap;
              a.vx = (a.vx || 0) - dx * overlap;
            }
            if (a.fy == null) {
              a.y -= dy * overlap;
              a.vy = (a.vy || 0) - dy * overlap;
            }
            if (b.fx == null) {
              b.x += dx * overlap;
              b.vx = (b.vx || 0) + dx * overlap;
            }
            if (b.fy == null) {
              b.y += dy * overlap;
              b.vy = (b.vy || 0) + dy * overlap;
            }
          }
        }
      }
    };
    fg.d3Force("collide", collideForce);

    // 2. Gentle Gravity: keep disconnected nodes in view without squishing
    const d3f = (fg as any).d3Force;
    if (d3f) {
      const gravityForce = (axis: "x" | "y") => {
        const strength = 0.02; // Gentle center pull
        return (alpha: number) => {
          const gData = fg.graphData();
          if (!gData || !gData.nodes) return;
          gData.nodes.forEach((node: any) => {
            if (node.fx != null || node.fy != null) return;
            const pos = node[axis];
            if (pos == null || !Number.isFinite(pos)) return;
            const v = axis === "x" ? "vx" : "vy";
            const currentV = node[v];
            const safeV = currentV != null && Number.isFinite(currentV) ? currentV : 0;
            node[v] = safeV + (0 - pos) * strength * alpha;
          });
        };
      };
      fg.d3Force("gravityX", gravityForce("x"));
      fg.d3Force("gravityY", gravityForce("y"));
    }
  }, [data, mode, dynamicCharge, dynamicDistance, nodeRadius]);

  // Apply forces to 3D graph
  const tuneForces = useCallback(() => {
    const fg = fg3dRef.current;
    if (!fg) return;
    fg.d3Force("charge")?.strength(dynamicCharge * 1.5);
    fg.d3Force("link")?.distance(dynamicDistance * 1.8);

    const gravity3D = (axis: "x" | "y" | "z") => {
      const strength = 0.02;
      return (alpha: number) => {
        const gData = fg.graphData();
        if (!gData || !gData.nodes) return;
        gData.nodes.forEach((node: any) => {
          if (node.fx != null || node.fy != null || node.fz != null) return;
          const pos = node[axis];
          if (pos == null || !Number.isFinite(pos)) return;
          const v = `v${axis}`;
          const currentV = node[v];
          const safeV = currentV != null && Number.isFinite(currentV) ? currentV : 0;
          node[v] = safeV + (0 - pos) * strength * alpha;
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

  const fitView = useCallback((ms = 600) => {
    if (mode === "3d") {
      fg3dRef.current?.zoomToFit(ms, 6);
    } else {
      fg2dRef.current?.zoomToFit(ms, 30);
    }
  }, [mode]);

  // Smooth fast zoom-out transition when switching between 2D and 3D
  useEffect(() => {
    const timer = setTimeout(() => {
      fitView(600);
    }, 250);
    return () => clearTimeout(timer);
  }, [mode, data, fitView]);

  /* ─────────────  /* ──────────────────────────────────────────────
     3D: Custom THREE.Group — sphere + billboard text ABOVE (selective LOD)
     ────────────────────────────────────────────── */
  const nodeThreeObject = useCallback(
    (node: any) => {
      const group = new THREE.Group();
      const r = nodeRadius(node.id);

      // Sphere geometry & material
      const geometry = new THREE.SphereGeometry(r, 12, 12);
      const material = new THREE.MeshLambertMaterial({
        color: communityColor(node.community),
        transparent: true,
        opacity: 0.92,
      });
      group.add(new THREE.Mesh(geometry, material));

      // Level of detail: Only build heavy SpriteText textures for hubs / high-degree nodes or smaller graphs
      const degree = nodeDegree.get(node.id) || 1;
      const isHub =
        node.id.startsWith("hub") || node.id.startsWith("subhub") || degree >= 4;

      if (nodeCount <= 200 || isHub) {
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
      }
      return group;
    },
    [nodeRadius, nodeDegree, nodeCount],
  );

  /* ──────────────────────────────────────────────
     2D: Canvas rendering — visible nodes + always-on labels
     ────────────────────────────────────────────── */
  const nodeCanvasObject = useCallback(
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      if (!Number.isFinite(node.x) || !Number.isFinite(node.y)) return;
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
        nodeCount <= 400 ||
        globalScale >= 0.5 ||
        (degree >= 3 && globalScale >= 0.25);

      if (showLabel) {
        const fontSize = Math.min(4.5, 8 / globalScale);
        ctx.font = `600 ${fontSize}px Inter, sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "top";

        const textWidth = ctx.measureText(label).width;
        const px = 3 / globalScale;
        const py = 1.5 / globalScale;
        const gap = 2.5 / globalScale;

        const pillY = node.y + r + gap;
        const pillW = textWidth + px * 2;
        const pillH = fontSize + py * 2;
        const pillX = node.x - pillW / 2;

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
          onClick={() => fitView(600)}
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
          linkDirectionalArrowLength={5}
          linkDirectionalArrowRelPos={0.88}
          linkDirectionalArrowColor={() => "#818cf8"}
          linkDirectionalParticles={nodeCount > 400 ? 0 : 2}
          linkDirectionalParticleSpeed={0.006}
          linkDirectionalParticleWidth={1.8}
          linkDirectionalParticleColor={() => "#c084fc"}
          linkColor={() => "rgba(129, 140, 248, 0.55)"}
          linkOpacity={0.6}
          linkWidth={1.0}
          cooldownTicks={60}
          warmupTicks={30}
          d3AlphaDecay={0.06}
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
          enableNodeDrag={true}
          onNodeDrag={(node: any) => {
            node.fx = node.x;
            node.fy = node.y;
            node.fz = node.z;
          }}
          onNodeDragEnd={(node: any) => {
            node.fx = node.x;
            node.fy = node.y;
            node.fz = node.z;
          }}
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
          nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D) => {
            const r = nodeRadius(node.id) + 2;
            ctx.beginPath();
            ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
            ctx.fillStyle = color;
            ctx.fill();
          }}
          linkDirectionalArrowLength={5}
          linkDirectionalArrowRelPos={0.88}
          linkDirectionalArrowColor={() => "#6366f1"}
          linkDirectionalParticles={nodeCount > 400 ? 0 : 2}
          linkDirectionalParticleSpeed={0.006}
          linkDirectionalParticleWidth={2.0}
          linkDirectionalParticleColor={() => "#818cf8"}
          linkColor={() => "rgba(129, 140, 248, 0.6)"}
          linkWidth={1.4}
          height={height}
          width={width}
          cooldownTicks={60}
          warmupTicks={30}
          d3AlphaDecay={0.04}
          d3VelocityDecay={0.35}
          enableNodeDrag={true}
          onNodeDrag={(node: any) => {
            node.fx = node.x;
            node.fy = node.y;
          }}
          onNodeDragEnd={(node: any) => {
            node.fx = node.x;
            node.fy = node.y;
          }}
          enableZoomInteraction={true}
          onNodeClick={onNodeClick}
          onEngineStop={() => {
            if (!didInitialFit.current) {
              didInitialFit.current = true;
              fitView(600);
            }
          }}
        />
      )}
    </div>
  );
}

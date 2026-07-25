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

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
});

export interface GraphData {
  nodes: { id: string; name: string; type?: string; community?: number; size?: number; file?: string }[];
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
  cooldownTicks?: number;
  onNodeClick?: (node: any) => void;
}

export default function CodeGraph({
  data,
  height = 580,
  cooldownTicks = 220,
  onNodeClick,
}: CodeGraphProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  const fg3dRef = useRef<any>(null);
  const fg2dRef = useRef<any>(null);
  const didInitialFit = useRef(false);
  const didTuneForces = useRef(false);
  const [width, setWidth] = useState(760);
  const [mode, setMode] = useState<"3d" | "2d">("2d");
  const [selectedNode, setSelectedNode] = useState<any>(null);

  useEffect(() => {
    if (!ref.current) return;
    const resize = () =>
      setWidth(Math.max(320, ref.current?.clientWidth ?? 760));
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  // Compute node degree to calculate node size and collision radii
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

  /* Calculate dynamic force repulsion based on codebase massiveness & canvas size */
  const nodeCount = Math.max(1, data.nodes.length);
  const dynamicCharge = useMemo(() => {
    return -Math.max(450, Math.min(2000, ((width * height) / nodeCount) * 0.5));
  }, [width, height, nodeCount]);

  const dynamicDistance = useMemo(() => {
    return Math.max(100, Math.min(300, (Math.min(width, height) / Math.sqrt(nodeCount)) * 1.6));
  }, [width, height, nodeCount]);

  // Apply dynamic force repulsion and collision detection to 2D Graph
  useEffect(() => {
    const fg2d = fg2dRef.current;
    if (fg2d && mode === "2d") {
      fg2d.d3Force("charge")?.strength(dynamicCharge);
      fg2d.d3Force("link")?.distance(dynamicDistance);
    }
  }, [data, mode, dynamicCharge, dynamicDistance]);

  // Apply dynamic forces to 3D Graph
  const tuneForces = useCallback(() => {
    const fg = fg3dRef.current;
    if (!fg) return;
    fg.d3Force("charge")?.strength(dynamicCharge);
    fg.d3Force("link")?.distance(dynamicDistance);
  }, [dynamicCharge, dynamicDistance]);

  useEffect(() => {
    didInitialFit.current = false;
    didTuneForces.current = false;
  }, [data]);

  const fitView = useCallback((ms = 800) => {
    fg3dRef.current?.zoomToFit(ms, 45);
  }, []);

  /* 3D Custom Group rendering: Sphere + Text Sprite mounted strictly above sphere */
  const nodeThreeObject = useCallback(
    (node: any) => {
      const group = new THREE.Group();
      const degree = nodeDegree.get(node.id) || 1;
      const sphereRadius = Math.max(3.5, Math.sqrt(degree) * 1.4);

      // 1. Glowing 3D Sphere Mesh
      const geometry = new THREE.SphereGeometry(sphereRadius, 16, 16);
      const material = new THREE.MeshLambertMaterial({
        color: communityColor(node.community),
        transparent: true,
        opacity: 0.95,
      });
      const sphereMesh = new THREE.Mesh(geometry, material);
      group.add(sphereMesh);

      // 2. Billboarded Text Sprite placed strictly ABOVE the sphere
      const labelText = node.name || node.id;
      const sprite = new SpriteText(labelText);
      sprite.color = "#ffffff";
      sprite.backgroundColor = "rgba(15, 23, 42, 0.9)";
      sprite.padding = [2, 5];
      sprite.borderRadius = 4;
      sprite.borderWidth = 0.5;
      sprite.borderColor = "rgba(255, 255, 255, 0.3)";
      sprite.fontWeight = "600";
      sprite.fontFace = "Inter, sans-serif";
      sprite.textHeight = Math.min(4.5 + Math.sqrt(degree) * 0.5, 8.5);

      // Position sprite strictly ABOVE top edge of sphere
      (sprite as any).position.y = sphereRadius + (sprite.textHeight / 2) + 2.5;

      const mat = (sprite as any).material;
      if (mat) {
        mat.depthTest = true;
        mat.depthWrite = false;
        (sprite as any).renderOrder = 999;
      }

      group.add(sprite);
      return group;
    },
    [nodeDegree],
  );

  /* Fly camera to clicked node and open Inspector HUD */
  const handleNodeClick = useCallback(
    (node: any) => {
      setSelectedNode(node);
      if (mode === "3d") {
        const fg = fg3dRef.current;
        if (fg && Number.isFinite(node.x)) {
          const distance = 95;
          const len = Math.hypot(node.x, node.y, node.z) || 1;
          const ratio = 1 + distance / len;
          fg.cameraPosition(
            { x: node.x * ratio, y: node.y * ratio, z: node.z * ratio },
            node,
            1200,
          );
        }
      }
      onNodeClick?.(node);
    },
    [mode, onNodeClick],
  );

  /* 2D Canvas rendering with mathematical non-overlapping pill positioning */
  const nodeCanvasObject = useCallback(
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const label = node.name || node.id;
      const degree = nodeDegree.get(node.id) || 1;
      const r = Math.max(4, Math.sqrt(degree) * 1.7) + (1 / globalScale);

      // 1. Outer glowing halo ring
      ctx.beginPath();
      ctx.arc(node.x, node.y, r + 2.5 / globalScale, 0, 2 * Math.PI);
      ctx.fillStyle = communityColor(node.community);
      ctx.globalAlpha = 0.25;
      ctx.fill();
      ctx.globalAlpha = 1.0;

      // 2. Main Node circle
      ctx.beginPath();
      ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
      ctx.fillStyle = communityColor(node.community);
      ctx.fill();

      // 3. Crisp white node border
      ctx.lineWidth = 1 / globalScale;
      ctx.strokeStyle = "#ffffff";
      ctx.stroke();

      // 4. Dynamic Level of Detail (LOD) Text Pill rendering
      // Text Pill starts strictly BELOW node circle at y = node.y + r + gap
      const shouldRenderLabel =
        globalScale >= 0.55 || (degree >= 4 && globalScale >= 0.3);

      if (shouldRenderLabel) {
        const fontSize = Math.min(Math.max(8.5 / globalScale, 2.5), 11);
        ctx.font = `600 ${fontSize}px Inter, sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "top";

        const textWidth = ctx.measureText(label).width;
        const paddingX = 5 / globalScale;
        const paddingY = 2.5 / globalScale;

        // Top of pill box is strictly BELOW bottom edge of node circle (node.y + r)
        const gap = 3 / globalScale;
        const rectY = node.y + r + gap;
        const rectW = textWidth + paddingX * 2;
        const rectH = fontSize + paddingY * 2;
        const rectX = node.x - textWidth / 2 - paddingX;

        // Dark pill background
        ctx.fillStyle = "rgba(15, 23, 42, 0.9)";
        ctx.strokeStyle = "rgba(255, 255, 255, 0.3)";
        ctx.lineWidth = 0.5 / globalScale;

        ctx.beginPath();
        if (typeof (ctx as any).roundRect === "function") {
          (ctx as any).roundRect(rectX, rectY, rectW, rectH, 3.5 / globalScale);
        } else {
          ctx.rect(rectX, rectY, rectW, rectH);
        }
        ctx.fill();
        ctx.stroke();

        // White text inside pill box
        ctx.fillStyle = "#ffffff";
        ctx.fillText(label, node.x, rectY + paddingY);
      }
    },
    [nodeDegree],
  );

  // Find connected neighbors of selected node
  const selectedNeighbors = useMemo(() => {
    if (!selectedNode) return [];
    const nodeId = selectedNode.id;
    const neighbors: { node: any; direction: "in" | "out" }[] = [];

    data.links.forEach((l) => {
      const sId = typeof l.source === "object" ? l.source.id : l.source;
      const tId = typeof l.target === "object" ? l.target.id : l.target;

      if (sId === nodeId) {
        const targetNode = data.nodes.find((n) => n.id === tId);
        if (targetNode) neighbors.push({ node: targetNode, direction: "out" });
      } else if (tId === nodeId) {
        const sourceNode = data.nodes.find((n) => n.id === sId);
        if (sourceNode) neighbors.push({ node: sourceNode, direction: "in" });
      }
    });

    return neighbors;
  }, [selectedNode, data]);

  if (data.nodes.length === 0)
    return (
      <p className="text-sm text-slate-500">Nothing to visualize yet.</p>
    );

  return (
    <div
      ref={ref}
      className="relative overflow-hidden rounded-lg border border-slate-200 bg-slate-950 shadow-inner"
      style={{ height }}
    >
      {/* Controls: Reset view + 2D/3D Mode Toggle */}
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
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-300 hover:bg-slate-700/60"
              }`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      {/* Navigation & LOD Info Bar */}
      <div className="pointer-events-none absolute bottom-3 left-3 z-10 rounded-md bg-slate-900/85 px-3 py-1.5 text-[11px] text-slate-300 backdrop-blur border border-slate-800">
        {mode === "3d"
          ? "3D View · Drag to rotate · Scroll to zoom · Right-drag to pan · Click node to inspect"
          : "2D View · Zero-overlap labels · Click node to open inspector"}
      </div>

      {/* Floating Node Inspector HUD Drawer */}
      {selectedNode && (
        <div className="absolute bottom-3 right-3 z-20 w-80 rounded-lg border border-slate-700/80 bg-slate-900/95 p-3.5 shadow-2xl backdrop-blur text-xs text-slate-200 animate-in fade-in slide-in-from-bottom-2">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-2">
            <span className="font-semibold text-sm text-indigo-400 flex items-center gap-1.5 truncate">
              <span
                className="h-2.5 w-2.5 rounded-full inline-block shrink-0"
                style={{ backgroundColor: communityColor(selectedNode.community) }}
              />
              {selectedNode.name || selectedNode.id}
            </span>
            <button
              onClick={() => setSelectedNode(null)}
              className="text-slate-400 hover:text-white p-0.5 text-sm leading-none"
            >
              ✕
            </button>
          </div>

          <div className="space-y-1.5 text-[11px] text-slate-300">
            <p className="font-mono text-slate-400 truncate">{selectedNode.file || selectedNode.id}</p>
            <div className="flex items-center gap-2 pt-1">
              <span className="rounded bg-slate-800 px-2 py-0.5 text-slate-300">
                Community C{selectedNode.community ?? "?"}
              </span>
              <span className="rounded bg-slate-800 px-2 py-0.5 text-slate-300">
                Degree: {nodeDegree.get(selectedNode.id) || 1}
              </span>
            </div>

            {selectedNeighbors.length > 0 && (
              <div className="pt-2">
                <p className="font-semibold text-slate-400 mb-1">
                  Connected Modules ({selectedNeighbors.length}):
                </p>
                <div className="max-h-32 overflow-y-auto space-y-1 pr-1">
                  {selectedNeighbors.slice(0, 8).map(({ node, direction }) => (
                    <button
                      key={node.id}
                      onClick={() => handleNodeClick(node)}
                      className="w-full text-left flex items-center justify-between rounded bg-slate-800/60 px-2 py-1 hover:bg-indigo-950/60 transition"
                    >
                      <span className="truncate text-slate-200">{node.name || node.id}</span>
                      <span className="text-[10px] text-indigo-400 font-mono ml-1">
                        {direction === "out" ? "→ depends" : "← caller"}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

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
          nodeThreeObject={nodeThreeObject}
          nodeThreeObjectExtend={false}
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
          onNodeClick={handleNodeClick}
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
            const r = Math.max(4, Math.sqrt(degree) * 1.7) + 3;
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
          warmupTicks={40}
          d3AlphaDecay={0.012}
          d3VelocityDecay={0.25}
          enableNodeDrag={true}
          enableZoomInteraction={true}
          onNodeClick={handleNodeClick}
        />
      )}
    </div>
  );
}

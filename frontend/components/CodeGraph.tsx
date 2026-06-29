"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
});

export interface GraphData {
  nodes: { id: string; name: string; type?: string }[];
  links: { source: string; target: string }[];
}

export default function CodeGraph({ data }: { data: GraphData }) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [width, setWidth] = useState(760);

  useEffect(() => {
    if (!ref.current) return;
    const resize = () => setWidth(Math.max(320, ref.current?.clientWidth ?? 760));
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  if (data.nodes.length === 0)
    return (
      <p className="text-sm text-slate-500">Nothing to visualize yet.</p>
    );

  return (
    <div ref={ref} className="overflow-hidden rounded-lg border border-slate-200 bg-white">
      <ForceGraph2D
        graphData={data}
        nodeLabel="name"
        nodeAutoColorBy="type"
        linkDirectionalArrowLength={4}
        linkDirectionalArrowRelPos={1}
        height={520}
        width={width}
      />
    </div>
  );
}

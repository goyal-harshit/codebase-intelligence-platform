"use client";

import dynamic from "next/dynamic";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
});

export interface GraphData {
  nodes: { id: string; name: string; type?: string }[];
  links: { source: string; target: string }[];
}

export default function CodeGraph({ data }: { data: GraphData }) {
  if (data.nodes.length === 0)
    return (
      <p className="text-gray-500 text-sm">Nothing to visualize yet.</p>
    );

  return (
    <div className="border rounded-lg bg-white overflow-hidden">
      <ForceGraph2D
        graphData={data}
        nodeLabel="name"
        nodeAutoColorBy="type"
        linkDirectionalArrowLength={4}
        linkDirectionalArrowRelPos={1}
        height={520}
        width={760}
      />
    </div>
  );
}

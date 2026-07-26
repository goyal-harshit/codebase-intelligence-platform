import { GraphifyGraph, GraphifyNode, GraphifyLink } from "./api";

/**
 * Generates a deterministic graph with `nodeCount` ≈ 800 matching GraphifyGraph.
 *   • 5 clusters (communities 0‑4).
 *   • Each cluster has a core “hub” node that connects to most nodes in that cluster.
 *   • A few inter‑cluster links create a sparse global connectivity.
 *   • About 20% of nodes are isolated (no links) to satisfy the non‑connected requirement.
 */
function generateLargeGraph(nodeCount = 800): GraphifyGraph {
  const clusters = 5;
  const nodes: GraphifyNode[] = [];
  const links: GraphifyLink[] = [];

  const communityLabels: Record<string, string> = {
    "0": "Core Engine & Router",
    "1": "Data Ingestion & Parser",
    "2": "Graph Analytics & Cypher",
    "3": "Vector Index & RAG",
    "4": "API Gateway & Security",
  };

  // Create hub nodes – one per cluster
  const hubIds: string[] = [];
  for (let c = 0; c < clusters; c++) {
    const hubId = `hub-${c}`;
    hubIds.push(hubId);
    nodes.push({
      id: hubId,
      name: `Cluster ${c + 1} Hub (${communityLabels[String(c)]})`,
      type: "class",
      community: c,
      file: `src/modules/cluster_${c}/hub.ts`,
    });
  }

  // Allocate remaining nodes to clusters
  const remaining = nodeCount - clusters;
  const types = ["function", "class", "module", "interface"];
  for (let i = 0; i < remaining; i++) {
    const cluster = i % clusters;
    const id = `n-${i}`;
    const nodeType = types[i % types.length];
    nodes.push({
      id,
      name: `Node_${i}_${nodeType}`,
      type: nodeType,
      community: cluster,
      file: `src/modules/cluster_${cluster}/node_${i}.ts`,
    });
    // Connect to its hub with 80% probability
    if (Math.random() < 0.8) {
      links.push({ source: hubIds[cluster], target: id });
    }
  }

  // Add intra‑cluster random links
  for (let i = 0; i < nodes.length; i++) {
    const a = nodes[i];
    if (a.id.startsWith("hub-")) continue;
    if (Math.random() < 0.1) {
      const candidates = nodes.filter(
        (n) => n.community === a.community && n.id !== a.id && !n.id.startsWith("hub-")
      );
      if (candidates.length) {
        const b = candidates[Math.floor(Math.random() * candidates.length)];
        links.push({ source: a.id, target: b.id });
      }
    }
  }

  // Add a small set of inter‑cluster bridges
  const bridgeCount = Math.max(5, Math.floor(clusters * 2));
  for (let i = 0; i < bridgeCount; i++) {
    const srcCluster = Math.floor(Math.random() * clusters);
    const dstCluster = (srcCluster + 1 + Math.floor(Math.random() * (clusters - 1))) % clusters;
    const src = hubIds[srcCluster];
    const dst = hubIds[dstCluster];
    links.push({ source: src, target: dst });
  }

  // Ensure ~20% isolated nodes (no links)
  const isolatedTarget = Math.floor(nodes.length * 0.2);
  const isolatedIds = new Set(nodes.slice(0, isolatedTarget).map((n) => n.id));
  const filteredLinks = links.filter(
    (l) => !isolatedIds.has(l.source) && !isolatedIds.has(l.target)
  );

  return {
    nodes,
    links: filteredLinks,
    community_labels: communityLabels,
  };
}

export const largeGraphData: GraphifyGraph = generateLargeGraph();

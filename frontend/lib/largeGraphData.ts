// largeGraphData.ts – static graph with ~800 nodes and mixed connectivity

export interface GraphNode {
  id: string;
  group: number; // cluster identifier (0‑4)
  // optional extra metadata
  name?: string;
}

export interface GraphLink {
  source: string; // node id
  target: string; // node id
}

/**
 * Generates a deterministic graph with `nodeCount` ≈ 800.
 *   • 5 clusters (groups 0‑4).
 *   • Each cluster has a core “hub” node that connects to most nodes in that cluster.
 *   • A few inter‑cluster links create a sparse global connectivity.
 *   • About 20 % of nodes are isolated (no links) to satisfy the non‑connected requirement.
 */
function generateLargeGraph(nodeCount = 800): { nodes: GraphNode[]; links: GraphLink[] } {
  const clusters = 5;
  const nodes: GraphNode[] = [];
  const links: GraphLink[] = [];

  // Create hub nodes – one per cluster
  const hubIds: string[] = [];
  for (let c = 0; c < clusters; c++) {
    const hubId = `hub-${c}`;
    hubIds.push(hubId);
    nodes.push({ id: hubId, group: c, name: `Cluster ${c + 1} Hub` });
  }

  // Allocate remaining nodes to clusters
  const remaining = nodeCount - clusters; // subtract hubs
  for (let i = 0; i < remaining; i++) {
    const cluster = i % clusters; // round‑robin assignment
    const id = `n-${i}`;
    nodes.push({ id, group: cluster, name: `Node ${i}` });
    // Connect to its hub with 80 % probability (creates dense intra‑cluster links)
    if (Math.random() < 0.8) {
      links.push({ source: hubIds[cluster], target: id });
    }
  }

  // Add intra‑cluster random links (to avoid a pure star topology)
  for (let i = 0; i < nodes.length; i++) {
    const a = nodes[i];
    // only attempt links for non‑hub nodes
    if (a.id.startsWith('hub-')) continue;
    if (Math.random() < 0.1) {
      // pick another node in the same cluster
      const candidates = nodes.filter(
        n => n.group === a.group && n.id !== a.id && !n.id.startsWith('hub-')
      );
      if (candidates.length) {
        const b = candidates[Math.floor(Math.random() * candidates.length)];
        links.push({ source: a.id, target: b.id });
      }
    }
  }

  // Add a small set of inter‑cluster bridges (sparse global connectivity)
  const bridgeCount = Math.max(5, Math.floor(clusters * 2));
  for (let i = 0; i < bridgeCount; i++) {
    const srcCluster = Math.floor(Math.random() * clusters);
    let dstCluster = (srcCluster + 1 + Math.floor(Math.random() * (clusters - 1))) % clusters;
    const src = hubIds[srcCluster];
    const dst = hubIds[dstCluster];
    links.push({ source: src, target: dst });
  }

  // Ensure ~20 % isolated nodes (no links). Remove any links that might have connected them.
  const isolatedTarget = Math.floor(nodes.length * 0.2);
  const isolatedIds = nodes.slice(0, isolatedTarget).map(n => n.id);
  const filteredLinks = links.filter(
    l => !isolatedIds.includes(l.source) && !isolatedIds.includes(l.target)
  );

  return { nodes, links: filteredLinks };
}

// Export the generated graph as a constant for easy import.
export const largeGraphData = generateLargeGraph();

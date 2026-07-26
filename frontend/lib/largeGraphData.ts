import { GraphifyGraph, GraphifyNode, GraphifyLink } from "./api";

/**
 * Generates a rich, high-performance graph dataset with 850 nodes and 1,200+ links.
 * Features:
 *   • 5 distinct community clusters with core hubs and sub-hubs.
 *   • Dense intra-cluster connections forming clear structural modules.
 *   • Inter-cluster bridge links for cross-module dependencies.
 *   • ~15% dedicated isolated leaf nodes (unconnected components).
 */
function generateLargeGraph(nodeCount = 850): GraphifyGraph {
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

  // 1. Create primary hub nodes – 1 core hub per cluster
  const hubIds: string[] = [];
  for (let c = 0; c < clusters; c++) {
    const hubId = `hub-${c}`;
    hubIds.push(hubId);
    nodes.push({
      id: hubId,
      name: `Core Hub (${communityLabels[String(c)]})`,
      type: "class",
      community: c,
      file: `src/modules/cluster_${c}/hub.ts`,
    });
  }

  // 2. Create sub-hubs – 3 sub-hubs per cluster (15 sub-hubs total)
  const subHubIds: Record<number, string[]> = { 0: [], 1: [], 2: [], 3: [], 4: [] };
  for (let c = 0; c < clusters; c++) {
    for (let s = 0; s < 3; s++) {
      const subId = `subhub-${c}-${s}`;
      subHubIds[c].push(subId);
      nodes.push({
        id: subId,
        name: `SubModule_${c}_${s}`,
        type: "module",
        community: c,
        file: `src/modules/cluster_${c}/sub_${s}.ts`,
      });
      // Connect sub-hub to primary cluster hub
      links.push({ source: hubIdForCluster(c), target: subId });
    }
  }

  function hubIdForCluster(c: number) {
    return `hub-${c}`;
  }

  // 3. Create regular connected nodes (~85% of total nodes)
  const isolatedCount = Math.floor(nodeCount * 0.15); // 15% isolated
  const connectedTarget = nodeCount - nodes.length - isolatedCount;
  const types = ["function", "class", "module", "interface"];

  for (let i = 0; i < connectedTarget; i++) {
    const cluster = i % clusters;
    const id = `node-${i}`;
    const nodeType = types[i % types.length];
    nodes.push({
      id,
      name: `Service_${i}_${nodeType}`,
      type: nodeType,
      community: cluster,
      file: `src/modules/cluster_${cluster}/service_${i}.ts`,
    });

    // Connect node to either the primary hub (70%) or a sub-hub (30%)
    if (Math.random() < 0.7) {
      links.push({ source: hubIdForCluster(cluster), target: id });
    } else {
      const subList = subHubIds[cluster];
      const targetSub = subList[i % subList.length];
      links.push({ source: targetSub, target: id });
    }

    // Add extra intra-cluster peer links with 15% probability for organic graph density
    if (Math.random() < 0.15 && i > 5) {
      const peerId = `node-${Math.max(0, i - (i % 7) - 1)}`;
      links.push({ source: id, target: peerId });
    }
  }

  // 4. Add strong inter-cluster bridges (connect hubs and sub-hubs across clusters)
  for (let c1 = 0; c1 < clusters; c1++) {
    for (let c2 = c1 + 1; c2 < clusters; c2++) {
      links.push({ source: hubIdForCluster(c1), target: hubIdForCluster(c2) });
      const sub1 = subHubIds[c1][0];
      const sub2 = subHubIds[c2][0];
      links.push({ source: sub1, target: sub2 });
    }
  }

  // 5. Create isolated leaf nodes (~15% of graph, strictly unlinked)
  for (let k = 0; k < isolatedCount; k++) {
    const cluster = k % clusters;
    const isoId = `isolated-${k}`;
    nodes.push({
      id: isoId,
      name: `Standalone_Util_${k}`,
      type: "function",
      community: cluster,
      file: `src/utils/standalone_${k}.ts`,
    });
  }

  return {
    nodes,
    links,
    community_labels: communityLabels,
  };
}

export const largeGraphData: GraphifyGraph = generateLargeGraph(850);

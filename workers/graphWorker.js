// graphWorker.js – runs d3-force-3d simulation off the main thread
// This script is loaded via importScripts in the worker context.

// Load d3-force-3d from CDN (no bundler needed in the worker)
self.importScripts('https://unpkg.com/d3-force-3d@3/dist/d3-force-3d.min.js');

let simulation = null;
let nodes = [];
let links = [];

// Helper to start / restart simulation
function startSimulation() {
  if (!nodes.length) return;
  // Create a fresh simulation each time we receive new data
  simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id((d) => d.id).distance(30))
    .force('charge', d3.forceManyBody().strength(-40))
    .force('center', d3.forceCenter(0, 0, 0))
    .force('collision', d3.forceCollide().radius((d) => d.r || 5))
    .alphaDecay(0.02)
    .on('tick', () => {
      // Send updated positions back to the main thread (throttled per tick)
      self.postMessage({ type: 'tick', payload: nodes.map(n => ({ id: n.id, x: n.x, y: n.y, z: n.z })) });
    })
    .on('end', () => {
      self.postMessage({ type: 'end' });
    });
}

self.onmessage = (event) => {
  const { type, payload } = event.data;
  if (type === 'init') {
    // payload: { nodes: [], links: [] }
    nodes = payload.nodes.map((n) => ({ ...n, x: Math.random() * 100 - 50, y: Math.random() * 100 - 50, z: Math.random() * 100 - 50 }));
    links = payload.links;
    // Attach radius for collision force (use degree if provided)
    const degreeMap = {};
    links.forEach(l => {
      degreeMap[l.source] = (degreeMap[l.source] || 0) + 1;
      degreeMap[l.target] = (degreeMap[l.target] || 0) + 1;
    });
    nodes.forEach(n => {
      const deg = degreeMap[n.id] || 1;
      n.r = Math.min(10, Math.max(4, 3.5 + Math.sqrt(deg) * 1.1));
    });
    startSimulation();
  } else if (type === 'stop') {
    if (simulation) simulation.stop();
  } else if (type === 'update') {
    // payload may contain incremental nodes/links – we simply restart for simplicity
    if (simulation) simulation.stop();
    nodes = payload.nodes.map((n) => ({ ...n, x: Math.random() * 100 - 50, y: Math.random() * 100 - 50, z: Math.random() * 100 - 50 }));
    links = payload.links;
    const degreeMap = {};
    links.forEach(l => {
      degreeMap[l.source] = (degreeMap[l.source] || 0) + 1;
      degreeMap[l.target] = (degreeMap[l.target] || 0) + 1;
    });
    nodes.forEach(n => {
      const deg = degreeMap[n.id] || 1;
      n.r = Math.min(10, Math.max(4, 3.5 + Math.sqrt(deg) * 1.1));
    });
    startSimulation();
  }
};

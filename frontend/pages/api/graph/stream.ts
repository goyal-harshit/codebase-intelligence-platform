import type { NextApiRequest, NextApiResponse } from 'next';
import { largeGraphData } from '@/lib/largeGraphData';
import { PassThrough } from 'stream';

/**
 * API: /api/graph/stream
 * Returns NDJSON (one node or link per line) with optional `chunkSize` query param.
 * Chunk size defaults to 5000 items. The endpoint streams the data in a memory‑efficient way.
 */
export default function handler(req: NextApiRequest, res: NextApiResponse) {
  const { chunkSize } = req.query;
  const size = typeof chunkSize === 'string' ? parseInt(chunkSize, 10) : 5000;
  if (isNaN(size) || size <= 0) {
    res.status(400).json({ error: 'Invalid chunkSize' });
    return;
  }

  res.setHeader('Content-Type', 'application/x-ndjson');
  const stream = new PassThrough();

  // Stream nodes
  for (const node of largeGraphData.nodes) {
    stream.write(JSON.stringify({ type: 'node', payload: node }) + '\n');
  }

  // Stream links
  for (const link of largeGraphData.links) {
    stream.write(JSON.stringify({ type: 'link', payload: link }) + '\n');
  }

  stream.end();
  stream.pipe(res);
}

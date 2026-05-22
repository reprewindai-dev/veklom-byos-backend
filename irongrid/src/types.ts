export interface GridNode {
  row: number;
  col: number;
  isStart: boolean;
  isEnd: boolean;
  isObstacle: boolean;
  // Multiplier for custom weights drawn by user (1 = flat, 5 = hill/high cost, Infinity = wall)
  weight: number;
  // Distance/potential field computed by gradient potential solver
  potential: number;
  // Visited state
  visited: boolean;
  // Path flag
  isPath: boolean;
  // 8-neighbor gradient vector towards lower potential
  gradientX?: number;
  gradientY?: number;
}

export type GridDimension = 10 | 25 | 50;

export interface BenchmarkMetrics {
  pythonTimeUs: number; // microseconds
  rustTimeUs: number;
  gridSize: number;
  speedup: number;
}

export interface QueueAgent {
  id: string;
  name: string;
  status: 'idle' | 'queued' | 'processing' | 'completed' | 'blocked' | 'error';
  progress: number;
  routeSize: number;
  processedBy: string | null; // Name of thread / worker process
  timeTakenUs: number;
  cpuPercent?: number;
  cpuHistory?: number[];
  errorMessage?: string;
}

export interface AuditRecord {
  id: string;
  timestamp: string;
  nodeX: number;
  nodeY: number;
  rawFloats: string; // e.g. [12.4, 45.8]
  binaryIEEE754: string; // Packed bit-stream (64-bit etc.)
  sha256: string; // SHA-256 hash or hash state accum
}

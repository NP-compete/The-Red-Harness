export interface TraceNode {
  spanId: string;
  name: string;
  durationMs: number;
  ownMs: number;
  attributes: Record<string, string>;
  children: TraceNode[];
}

export interface TraceState {
  roots: TraceNode[];
  orphans: string[];
  totalMs: number;
  slowest: string;
}

export interface TraceRow {
  spanId: string;
  name: string;
  depth: number;
  duration: string;
  own: string;
  share: number;
  slowest: boolean;
  attributes: { key: string; value: string }[];
}

export interface PresentedTrace {
  rows: TraceRow[];
  total: string;
  warning: string;
}

export function presentTrace(trace: TraceState): PresentedTrace {
  const rows: TraceRow[] = [];
  walk(trace.roots, 0, trace, rows);

  const lost = trace.orphans.length;

  return {
    rows,
    total: duration(trace.totalMs),
    warning:
      lost > 0
        ? `${lost} step${lost === 1 ? '' : 's'} lost ${lost === 1 ? 'its' : 'their'} parent and ${
            lost === 1 ? 'is' : 'are'
          } shown at the top`
        : '',
  };
}

function walk(nodes: TraceNode[], depth: number, trace: TraceState, into: TraceRow[]): void {
  for (const node of nodes) {
    into.push({
      spanId: node.spanId,
      name: node.name,
      depth,
      duration: duration(node.durationMs),
      // Time in the step itself, so a slow parent is not blamed for its child.
      own: duration(node.ownMs),
      share: trace.totalMs > 0 ? node.durationMs / trace.totalMs : 0,
      slowest: node.spanId === trace.slowest,
      attributes: Object.entries(node.attributes).map(([key, value]) => ({ key, value })),
    });
    walk(node.children, depth + 1, trace, into);
  }
}

function duration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

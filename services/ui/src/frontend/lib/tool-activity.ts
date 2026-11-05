export type CallState = 'running' | 'done' | 'failed' | 'awaiting';

export interface ToolCall {
  tool: string;
  state: CallState;
  ms: number;
  writes: boolean;
}

export interface ActivityStep {
  tool: string;
  status: CallState;
  took: string;
  changes: boolean;
}

export interface PresentedActivity {
  summary: string;
  steps: ActivityStep[];
  waiting: boolean;
  changing: number;
  slowest: string;
}

const SLOW_MS = 1000;

export function presentToolActivity(calls: ToolCall[]): PresentedActivity {
  const steps = calls.map<ActivityStep>((call) => ({
    tool: call.tool,
    status: call.state,
    took: call.ms > 0 ? `${(call.ms / 1000).toFixed(1)}s` : '',
    changes: call.writes,
  }));

  const slowest = [...calls].sort((a, b) => b.ms - a.ms)[0];

  return {
    // One line first: the detail is there for anybody who wants it, but
    // a wall of tool names is not an explanation.
    summary: summarise(calls),
    steps,
    waiting: calls.some((call) => call.state === 'awaiting'),
    changing: calls.filter((call) => call.writes).length,
    slowest:
      slowest && slowest.ms >= SLOW_MS
        ? `${slowest.tool} took ${(slowest.ms / 1000).toFixed(1)}s`
        : '',
  };
}

function summarise(calls: ToolCall[]): string {
  const systems = [...new Set(calls.filter((c) => !c.writes).map((c) => c.tool.split('.')[0]))];
  if (systems.length === 0) return '';
  if (systems.length === 1) return `Looked in ${systems[0]}`;
  return `Looked in ${systems.slice(0, -1).join(', ')} and ${systems[systems.length - 1]}`;
}

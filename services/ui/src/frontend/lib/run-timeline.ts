export type EventKind = 'started' | 'tool' | 'awaiting-approval' | 'finished';

export interface RunEvent {
  at: string;
  kind: EventKind;
  label: string;
}

export interface TimelineStep {
  label: string;
  kind: EventKind;
  at: string;
  took: string;
  waiting: boolean;
  slowest: boolean;
}

export interface PresentedTimeline {
  steps: TimelineStep[];
  total: string;
  waitingTotal: string;
  finished: boolean;
}

const DOMINATES = 0.5;

export function presentTimeline(events: RunEvent[]): PresentedTimeline {
  const ordered = [...events].sort((a, b) => Date.parse(a.at) - Date.parse(b.at));
  const seconds = ordered.map((event, index) =>
    index === ordered.length - 1
      ? null
      : (Date.parse(ordered[index + 1].at) - Date.parse(event.at)) / 1000,
  );

  const total = seconds.reduce<number>((sum, value) => sum + (value ?? 0), 0);
  const longest = Math.max(0, ...seconds.map((value) => value ?? 0));
  const waited = ordered.reduce<number>(
    (sum, event, index) =>
      event.kind === 'awaiting-approval' ? sum + (seconds[index] ?? 0) : sum,
    0,
  );

  return {
    steps: ordered.map((event, index) => ({
      label: event.label,
      kind: event.kind,
      at: event.at,
      took: seconds[index] === null ? '' : format(seconds[index] as number),
      waiting: event.kind === 'awaiting-approval',
      // Only called out when one step really is where the time went.
      slowest: total > 0 && seconds[index] === longest && longest / total > DOMINATES,
    })),
    total: ordered.length ? format(total) : '',
    waitingTotal: waited > 0 ? format(waited) : '',
    finished: ordered.some((event) => event.kind === 'finished'),
  };
}

function format(seconds: number): string {
  const whole = Math.round(seconds);
  if (whole < 60) return `${whole}s`;
  return `${Math.floor(whole / 60)}m ${whole % 60}s`;
}

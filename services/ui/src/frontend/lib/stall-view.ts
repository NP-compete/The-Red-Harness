export interface StallState {
  state: 'working' | 'stalled' | 'tool-hung' | 'waiting';
  quietForSeconds: number;
  needsAttention: boolean;
  reason: string;
  toolRunning: string;
}

export interface PresentedStall {
  /** Catalogue keys, not words: this runs where there is no
   *  translator. `count` drives the plural, `tool` the name. */
  headline: string;
  headlineCount: number;
  tool: string;
  detail: string;
  note: string;
  failed: false;
  severity: 'medium';
  action: 'stop';
}

export function presentStall(stall: StallState): PresentedStall | null {
  // Working is working, and waiting on a person is their time, not a fault.
  if (stall.state === 'working' || stall.state === 'waiting') return null;

  const hung = stall.state === 'tool-hung';

  const quiet = quietFor(stall.quietForSeconds);

  return {
    headline: hung ? 'stall.toolSlow' : quiet.key,
    headlineCount: hung ? 0 : quiet.count,
    tool: stall.toolRunning,
    detail: stall.reason,
    // The same promise the cancellation path makes: a call in flight finishes.
    note: hung ? 'stall.toolWillFinish' : '',
    failed: false,
    severity: 'medium',
    action: 'stop',
  };
}

/** Which key says how long it has been quiet, and the number for it. */
function quietFor(seconds: number): { key: string; count: number } {
  if (seconds < 60) return { key: 'stall.quietSeconds', count: seconds };
  return { key: 'stall.quietMinutes', count: Math.round(seconds / 60) };
}

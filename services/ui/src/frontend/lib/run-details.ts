export type RunState = 'running' | 'awaiting-approval' | 'finished' | 'failed';
export type RunAction = 'stop' | 'approve' | 'refuse';

export interface Run {
  id: string;
  state: RunState;
  model: string;
  startedAt: string;
  tokens: number;
  tokenLimit: number | null;
  actions: number;
  actionLimit: number | null;
  durable: boolean;
}

export interface PresentedRun {
  reference: string;
  state: string;
  tokens: string;
  actions: string;
  note: string;
  actionsAvailable: RunAction[];
  warning?: string;
}

const STATES: Record<RunState, string> = {
  running: 'Running',
  'awaiting-approval': 'Waiting for your approval',
  finished: 'Finished',
  failed: 'Did not finish',
};

const AVAILABLE: Record<RunState, RunAction[]> = {
  running: ['stop'],
  'awaiting-approval': ['approve', 'refuse'],
  finished: [],
  failed: [],
};

const WARN_AT = 0.9;

export function presentRunDetails(run: Run): PresentedRun {
  const nearlySpent =
    run.tokenLimit !== null && run.tokens / run.tokenLimit >= WARN_AT;

  return {
    // Enough of the reference to quote in a message, not so much that
    // it crowds out everything else.
    reference: `${run.id.slice(0, 8)}…`,
    state: STATES[run.state],
    tokens: against(run.tokens, run.tokenLimit),
    actions: against(run.actions, run.actionLimit),
    note: run.durable ? 'This run will survive a restart.' : '',
    actionsAvailable: AVAILABLE[run.state],
    warning: nearlySpent ? 'This run has nearly used its allowance.' : undefined,
  };
}

function against(used: number, limit: number | null): string {
  const shown = used.toLocaleString('en-US');
  return limit === null ? shown : `${shown} of ${limit.toLocaleString('en-US')}`;
}

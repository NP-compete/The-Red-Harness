export interface DeadlineState {
  remainingSeconds: number | null;
  limitSeconds: number | null;
  outcome: 'continue' | 'step-too-long' | 'out-of-time';
  warn: boolean;
  reason: string;
}

export interface PresentedDeadline {
  label: string;
  detail: string;
  fraction: number;
  urgent: boolean;
  failed: false;
  action: 'extend' | 'restart';
}

export function presentDeadline(state: DeadlineState): PresentedDeadline | null {
  if (state.remainingSeconds === null || state.limitSeconds === null) return null;

  const remaining = Math.max(0, state.remainingSeconds);
  const spent = state.limitSeconds - remaining;

  return {
    label: state.outcome === 'out-of-time' ? 'Out of time' : left(remaining),
    detail: state.reason,
    fraction: Math.min(1, spent / state.limitSeconds),
    urgent: state.warn,
    // Reaching the limit is the budget working, not the run breaking.
    failed: false,
    action: state.outcome === 'out-of-time' ? 'restart' : 'extend',
  };
}

function left(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)} seconds left`;
  const minutes = Math.round(seconds / 60);
  return `${minutes} minute${minutes === 1 ? '' : 's'} left`;
}

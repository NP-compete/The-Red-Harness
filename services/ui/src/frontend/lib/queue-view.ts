export interface QueueState {
  startsNow: boolean;
  position: number;
  estimatedWaitSeconds: number | null;
  refused: boolean;
  reason: string;
}

export interface PresentedQueue {
  headline: string;
  detail: string;
  estimate: string;
  estimateIsApproximate: boolean;
  started: false;
  severity: 'low' | 'medium';
  action: 'cancel' | 'retry-later';
}

export function presentQueue(state: QueueState): PresentedQueue | null {
  if (state.startsNow) return null;

  if (state.refused) {
    return {
      headline: 'Not queued',
      detail: state.reason,
      estimate: '',
      estimateIsApproximate: false,
      started: false,
      severity: 'medium',
      action: 'retry-later',
    };
  }

  return {
    headline: state.position === 1 ? 'Next in the queue' : `${ordinal(state.position)} in the queue`,
    detail: '',
    estimate: estimate(state.estimatedWaitSeconds),
    // Always labelled as a guess; a queue estimate that reads as a promise is a complaint.
    estimateIsApproximate: true,
    started: false,
    severity: 'low',
    action: 'cancel',
  };
}

function estimate(seconds: number | null): string {
  if (seconds === null) return '';
  if (seconds < 60) return 'under a minute';
  const minutes = Math.round(seconds / 60);
  return `about ${minutes} minute${minutes === 1 ? '' : 's'}`;
}

function ordinal(position: number): string {
  const suffixes = ['th', 'st', 'nd', 'rd'];
  const remainder = position % 100;
  const suffix =
    suffixes[(remainder - 20) % 10] ?? suffixes[remainder] ?? suffixes[0];
  return `${position}${suffix}`;
}

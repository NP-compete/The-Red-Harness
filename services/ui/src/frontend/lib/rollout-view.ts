export type RolloutState = 'advanced' | 'complete' | 'waiting' | 'halted' | 'rolled-back';

export interface RolloutStatus {
  version: string;
  previousVersion: string;
  share: number;
  steps: number[];
  state: RolloutState;
  reason: string;
  runs: number;
}

export interface PresentedRollout {
  headline: string;
  fallback: string;
  progress: string;
  detail: string;
  evidence: string;
  needsAttention: boolean;
  action: 'hold' | 'resume' | 'none';
}

export function presentRollout(status: RolloutStatus): PresentedRollout {
  const complete = status.state === 'complete';
  const rolledBack = status.state === 'rolled-back';

  return {
    headline: headline(status, rolledBack),
    fallback: complete || status.share >= 1 ? '' : `Everyone else is on ${status.previousVersion}`,
    progress: complete ? 'finished' : `step ${stepNumber(status)} of ${status.steps.length}`,
    detail: status.state === 'halted' ? 'This rollout is held where it is.' : status.reason,
    evidence: `${status.runs} runs so far`,
    needsAttention: rolledBack,
    action: complete ? 'none' : status.state === 'halted' ? 'resume' : 'hold',
  };
}

function headline(status: RolloutStatus, rolledBack: boolean): string {
  if (rolledBack) return `${status.version} was rolled back`;
  if (status.share <= 0) return `${status.version} is not serving any runs yet`;
  return `${status.version} is serving ${Math.round(status.share * 100)}% of runs`;
}

function stepNumber(status: RolloutStatus): number {
  const reached = status.steps.filter((step) => step <= status.share).length;
  return Math.max(reached, 1);
}

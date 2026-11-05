export type RunStage = 'thinking' | 'calling-tool' | 'awaiting-approval' | 'done';

export interface StoppableRun {
  stage: RunStage;
  tool: string;
  reversible: boolean;
  isOwner: boolean;
  isOperator: boolean;
}

export interface StopControl {
  enabled: boolean;
  label: string;
  confirm: string;
  blockedReason: string;
}

export function presentStopControl(run: StoppableRun): StopControl {
  const midWrite = run.stage === 'calling-tool' && !run.reversible;

  if (run.stage === 'done') {
    return {
      enabled: false,
      label: 'Stop',
      confirm: '',
      blockedReason: 'This run has already ended.',
    };
  }

  if (!run.isOwner && !run.isOperator) {
    return {
      enabled: false,
      label: 'Stop',
      confirm: '',
      blockedReason: 'This run is not yours to stop.',
    };
  }

  return {
    enabled: true,
    // The label promises only what will actually happen.
    label: midWrite ? 'Stop after this step' : 'Stop',
    confirm: confirmation(run, midWrite),
    blockedReason: '',
  };
}

function confirmation(run: StoppableRun, midWrite: boolean): string {
  const parts: string[] = [];
  if (midWrite) {
    parts.push(`${run.tool} cannot be undone, so it will finish before the run stops.`);
  }
  if (!run.isOwner) {
    parts.push('This run belongs to someone else.');
  }
  return parts.join(' ');
}

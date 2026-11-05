export interface UndoStep {
  target: string;
  kind: string;
}

export interface UndoResult {
  allUndone: boolean;
  failed: string[];
  message: string;
  warning: string;
}

export interface UndoPlan {
  steps: UndoStep[];
  cannotUndo: string[];
  complete: boolean;
  result: UndoResult | null;
}

export interface PresentedUndo {
  headline: string;
  steps: string[];
  leftBehind: string[];
  warning: string;
  confirmFirst: boolean;
  canRun: boolean;
  succeeded: boolean;
  severity: 'info' | 'high';
}

export function presentUndo(plan: UndoPlan): PresentedUndo {
  if (plan.result) {
    const clean = plan.result.allUndone;
    return {
      headline: plan.result.message,
      steps: [],
      // What failed is named, because putting it right is now a manual job.
      leftBehind: plan.result.failed,
      warning: plan.result.warning,
      confirmFirst: false,
      canRun: false,
      succeeded: clean,
      severity: clean ? 'info' : 'high',
    };
  }

  const count = plan.steps.length;
  const stuck = plan.cannotUndo.length;

  return {
    headline: count === 0 ? 'Nothing here can be undone' : `Undo ${count} change${count === 1 ? '' : 's'}`,
    steps: plan.steps.map((step) => step.target),
    leftBehind: plan.cannotUndo,
    warning: stuck > 0 ? `${stuck} change${stuck === 1 ? '' : 's'} cannot be undone and will stay` : '',
    // Undoing is itself a change to the world, so it is never one click.
    confirmFirst: true,
    canRun: count > 0,
    succeeded: false,
    severity: 'info',
  };
}

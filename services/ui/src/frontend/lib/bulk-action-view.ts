export interface BulkResult {
  done: number;
  skipped: number;
  failed: number;
  failedItems: string[];
  message: string;
}

export interface BulkPlan {
  action: string;
  count: number;
  runnable: boolean;
  needsConfirmation: boolean;
  confirmation: string;
  reason: string;
  result: BulkResult | null;
}

export interface PresentedBulkAction {
  headline: string;
  detail: string;
  confirmation: string;
  confirmFirst: boolean;
  canRun: boolean;
  succeeded: boolean;
  retryItems: string[];
  severity: 'none' | 'medium';
}

export function presentBulkAction(plan: BulkPlan): PresentedBulkAction {
  if (plan.result) {
    const clean = plan.result.failed === 0;
    return {
      headline: plan.result.message,
      detail: '',
      confirmation: '',
      confirmFirst: false,
      canRun: false,
      succeeded: clean,
      // Only the failures are offered again; redoing the successes risks doing them twice.
      retryItems: plan.result.failedItems,
      severity: clean ? 'none' : 'medium',
    };
  }

  return {
    headline: `${capitalise(plan.action)} ${plan.count} conversation${plan.count === 1 ? '' : 's'}`,
    detail: plan.runnable ? '' : plan.reason,
    confirmation: plan.confirmation,
    confirmFirst: plan.needsConfirmation,
    canRun: plan.runnable,
    succeeded: false,
    retryItems: [],
    severity: 'none',
  };
}

function capitalise(word: string): string {
  return word.charAt(0).toUpperCase() + word.slice(1);
}

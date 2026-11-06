export interface BudgetState {
  state: 'healthy' | 'at-risk' | 'exhausted' | 'unknown';
  used: number;
  failuresLeft: number;
  mayDeploy: boolean;
  warn: boolean;
  exceptional: boolean;
  reason: string;
}

export interface PresentedBudget {
  headline: string;
  detail: string;
  note: string;
  fraction: number | null;
  severity: 'none' | 'medium' | 'high';
  action: 'ship-fix' | 'none';
}

export function presentErrorBudget(budget: BudgetState): PresentedBudget {
  if (budget.state === 'unknown') {
    return {
      headline: 'Not enough history yet',
      detail: '',
      note: '',
      fraction: null,
      severity: 'none',
      action: 'none',
    };
  }

  const spent = budget.state === 'exhausted';

  return {
    // Phrased as what is left; a bar filling up reads as progress.
    headline: spent
      ? 'The error budget is spent'
      : `${Math.round((1 - budget.used) * 100)}% of the error budget left`,
    detail: spent
      ? 'Changes are paused until reliability recovers'
      : `${budget.failuresLeft} more failures before changes pause`,
    note: budget.exceptional ? 'Released while the budget was spent' : '',
    fraction: budget.used,
    severity: spent ? 'high' : budget.warn ? 'medium' : 'none',
    action: spent ? 'ship-fix' : 'none',
  };
}

export interface SpendDecision {
  permitted: boolean;
  runRemaining: string;
  periodRemaining: string;
  currency: string;
  warn: boolean;
  refusal: string | null;
  reason: string;
}

export interface PresentedSpendDecision {
  headline: string;
  detail: string;
  blocked: boolean;
  severity: 'medium' | 'high';
  action: 'raise-run-limit' | 'contact-admin' | 'wait' | 'none';
}

const HEADLINES: Record<string, string> = {
  'run-limit': 'This run has spent its limit',
  'period-limit': 'The budget for this period is spent',
  'fair-share': 'This is using more than its share of the budget',
};

// Who can unblock it differs by which limit was reached.
const ACTIONS: Record<string, PresentedSpendDecision['action']> = {
  'run-limit': 'raise-run-limit',
  'period-limit': 'contact-admin',
  'fair-share': 'wait',
};

export function presentSpendDecision(
  decision: SpendDecision,
): PresentedSpendDecision | null {
  if (decision.permitted && !decision.warn) return null;

  const money = (amount: string) =>
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: decision.currency,
    }).format(Number(amount));

  if (!decision.permitted && decision.refusal) {
    return {
      headline: HEADLINES[decision.refusal] ?? decision.reason,
      detail: `${money(decision.periodRemaining)} left in this period`,
      blocked: true,
      severity: 'high',
      action: ACTIONS[decision.refusal] ?? 'none',
    };
  }

  return {
    headline: `${money(decision.runRemaining)} left for this run`,
    detail: '',
    blocked: false,
    severity: 'medium',
    action: 'none',
  };
}

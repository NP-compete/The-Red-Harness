export interface ModelChoice {
  model: string;
  estimatedCost: number;
  currency: string;
  reason: string;
  refused: boolean;
  refusalReason: string;
}

export interface PresentedModelChoice {
  headline: string;
  detail: string;
  cost: string;
  severity: 'none' | 'high';
  action: 'shorten' | 'none';
}

export function presentModelChoice(choice: ModelChoice): PresentedModelChoice {
  if (choice.refused) {
    return {
      headline: 'This request cannot be run',
      detail: choice.refusalReason,
      cost: '',
      severity: 'high',
      action: /tokens/.test(choice.refusalReason) ? 'shorten' : 'none',
    };
  }

  return {
    headline: `Using ${choice.model}`,
    detail: choice.reason,
    cost: cost(choice.estimatedCost, choice.currency),
    severity: 'none',
    action: 'none',
  };
}

function cost(amount: number, currency: string): string {
  const format = (value: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(value);
  // Rounding a real charge to zero makes the whole figure untrustworthy.
  if (amount > 0 && amount < 0.01) return `under ${format(0.01)}`;
  return `about ${format(amount)}`;
}

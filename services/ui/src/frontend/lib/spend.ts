export interface Spend {
  total: string;
  currency: string;
  limit?: string;
  tokens?: number;
  byModel?: Record<string, string>;
  unpriced?: string[];
}

export interface SpendRow {
  model: string;
  amount: string;
}

export interface PresentedSpend {
  amount: string;
  tokens?: string;
  usedPercent?: number;
  overBudget: boolean;
  breakdown: SpendRow[];
  note?: string;
}

export function presentSpend(spend: Spend): PresentedSpend {
  const total = Number(spend.total);
  const limit = spend.limit === undefined ? undefined : Number(spend.limit);

  return {
    amount: money(spend.total, spend.currency),
    tokens: spend.tokens === undefined ? undefined : spend.tokens.toLocaleString('en-US'),
    usedPercent:
      limit === undefined || limit === 0
        ? undefined
        : Math.min(100, Math.round((total / limit) * 100)),
    overBudget: limit !== undefined && total > limit,
    breakdown: Object.entries(spend.byModel ?? {})
      .sort(([, a], [, b]) => Number(b) - Number(a))
      .map(([model, amount]) => ({ model, amount: money(amount, spend.currency) })),
    note:
      spend.unpriced && spend.unpriced.length > 0
        ? `Not included: ${spend.unpriced.join(', ')} — no price on record.`
        : undefined,
  };
}

function money(value: string, currency: string): string {
  // Small amounts matter here: rounding a fraction of a cent to zero
  // makes cheap-looking runs invisible in a total.
  const decimals = Math.max(2, (value.split('.')[1] ?? '').replace(/0+$/, '').length);
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(Number(value));
}

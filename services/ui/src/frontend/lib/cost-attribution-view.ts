export interface Charge {
  runId: string;
  chargedTo: string;
  person: string;
  amount: number;
  breakdown: Record<string, number>;
}

export interface ChargebackRow {
  chargedTo: string;
  total: string;
  runs: number;
  people: string[];
  subagentShare: string;
  unattributed: boolean;
}

export interface PresentedChargeback {
  rows: ChargebackRow[];
  total: string;
  emptyMessage: string;
}

const PLATFORM = 'platform';

export function presentChargeback(charges: Charge[], currency: string): PresentedChargeback {
  const money = (amount: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(amount);

  const byPayer = new Map<string, Charge[]>();
  for (const charge of charges) {
    byPayer.set(charge.chargedTo, [...(byPayer.get(charge.chargedTo) ?? []), charge]);
  }

  const rows = [...byPayer.entries()]
    .map(([chargedTo, group]) => {
      const total = group.reduce((sum, charge) => sum + charge.amount, 0);
      const subagents = group.reduce(
        (sum, charge) =>
          sum +
          Object.entries(charge.breakdown)
            .filter(([name]) => name !== 'main')
            .reduce((inner, [, amount]) => inner + amount, 0),
        0,
      );

      return {
        chargedTo,
        total: money(total),
        runs: group.length,
        people: [...new Set(group.map((charge) => charge.person))].sort(),
        // Shown only where fan-out actually happened, so it means something.
        subagentShare: subagents > 0 ? `${Math.round((subagents / total) * 100)}%` : '',
        unattributed: chargedTo === PLATFORM,
        _total: total,
      };
    })
    .sort((a, b) => b._total - a._total)
    .map(({ _total, ...row }) => row);

  return {
    rows,
    total: money(charges.reduce((sum, charge) => sum + charge.amount, 0)),
    emptyMessage: charges.length === 0 ? 'No spending recorded' : '',
  };
}

export interface CostReport {
  total_cost: string | null;
  currency: string;
  rate_card_version: string;
  unpriced: string[];
  complete: boolean;
}

export interface PresentedCost {
  /** Null when nothing could be priced. Never "0". */
  total: string | null;
  currency: string;
  rateCard: string;
  /** The total is a floor: some rows had no price. */
  atLeast: boolean;
  unpriced: string[];
  noRateCard: boolean;
  /** One row's cost, as a cell. */
  cell: (cost: string | null) => string;
}

// What the agent reports when no prices are configured at all.
const NO_CARD = "none";

/**
 * Money, said in a way that cannot flatter the bill.
 *
 * Every mistake available here makes spend look smaller than it
 * is — an unpriced model shown as zero, a partial total shown as
 * the total, a sub-cent amount rounded away — so each one says
 * something instead of quietly rendering a number.
 */
export function presentCost(report: CostReport): PresentedCost {
  return {
    total: report.total_cost === null ? null : money(report.total_cost),
    currency: report.currency,
    rateCard: report.rate_card_version,
    // Shown plainly as "the total", somebody budgets against it.
    atLeast: !report.complete && report.total_cost !== null,
    unpriced: report.unpriced,
    noRateCard: report.rate_card_version === NO_CARD || report.total_cost === null,
    cell: (cost) => {
      // A dash, not 0.00: that reads as "this model was free".
      if (cost === null) return "—";
      const amount = Number(cost);
      if (amount === 0) return "0.00";
      // Below a cent is still spend. Rounding it to 0.00 and
      // summing a thousand of them loses real money.
      if (amount < 0.005) return "<0.01";
      return money(cost);
    },
  };
}

function money(amount: string): string {
  return Number(amount).toFixed(2);
}

export type CapacityStatus = 'ok' | 'warn' | 'fail' | 'unknown';

export interface Tier {
  name: string;
  target: string;
  measured?: string;
  goodput?: number;
  providerBound?: boolean;
}

export interface CapacityRow {
  name: string;
  target: string;
  measured: string;
  goodput?: number;
  status: CapacityStatus;
  note?: string;
}

export interface PresentedCapacity {
  rows: CapacityRow[];
  overall: CapacityStatus;
}

const HEALTHY = 99;
const ACCEPTABLE = 95;

const SEVERITY: Record<CapacityStatus, number> = { ok: 0, unknown: 1, warn: 2, fail: 3 };

export function presentCapacity(tiers: Tier[]): PresentedCapacity {
  const rows = tiers.map<CapacityRow>((tier) => ({
    name: tier.name,
    target: tier.target,
    measured: tier.measured ?? 'not measured',
    goodput: tier.goodput,
    status: statusFor(tier),
    note: tier.providerBound
      ? 'In production this is bounded by your model provider quota.'
      : undefined,
  }));

  const overall = rows.reduce<CapacityStatus>(
    (worst, row) => (SEVERITY[row.status] > SEVERITY[worst] ? row.status : worst),
    'unknown',
  );

  return { rows, overall: rows.length === 0 ? 'unknown' : overall };
}

function statusFor(tier: Tier): CapacityStatus {
  if (tier.goodput === undefined) return 'unknown';
  if (tier.goodput >= HEALTHY) return 'ok';
  if (tier.goodput >= ACCEPTABLE) return 'warn';
  return 'fail';
}

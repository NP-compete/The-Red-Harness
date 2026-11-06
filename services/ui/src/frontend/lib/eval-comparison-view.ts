export interface ComparisonState {
  verdict: 'improved' | 'regressed' | 'no-change' | 'inconclusive';
  broken: string[];
  fixed: string[];
  beforeRate: number;
  afterRate: number;
  summary: string;
  reason: string;
  beforeVersion: string;
  afterVersion: string;
}

export interface PresentedComparison {
  headline: string;
  detail: string;
  rates: string;
  openCases: string[];
  canPromote: boolean;
  severity: 'none' | 'high';
}

export function presentComparison(comparison: ComparisonState): PresentedComparison {
  const broke = comparison.broken.length;
  const fixed = comparison.fixed.length;

  return {
    // What stopped working leads, whatever else improved alongside it.
    headline: broke > 0
      ? `${broke} case${broke === 1 ? '' : 's'} stopped working`
      : fixed > 0
        ? `${fixed} case${fixed === 1 ? '' : 's'} started working`
        : `No change between ${comparison.beforeVersion} and ${comparison.afterVersion}`,
    detail: detail(comparison, broke, fixed),
    rates: `${percent(comparison.beforeRate)} → ${percent(comparison.afterRate)}`,
    openCases: comparison.broken,
    canPromote: comparison.verdict === 'improved' || comparison.verdict === 'no-change',
    severity: broke > 0 ? 'high' : 'none',
  };
}

function detail(comparison: ComparisonState, broke: number, fixed: number): string {
  if (comparison.verdict === 'inconclusive') return comparison.reason;
  if (broke > 0 && fixed > 0) return `${fixed} case${fixed === 1 ? '' : 's'} started working`;
  return '';
}

function percent(rate: number): string {
  return `${Math.round(rate * 100)}%`;
}

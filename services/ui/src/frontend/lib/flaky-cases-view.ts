export interface CaseResult {
  stability: 'steady' | 'flaky' | 'unknown';
  passes: boolean;
  passRate: number;
  attempts: number;
  reason: string;
}

export interface FlakinessState {
  cases: Record<string, CaseResult>;
  flaky: string[];
  flakyShare: number;
  worst: string;
  mayGate: boolean;
}

export interface FlakyRow {
  caseId: string;
  description: string;
  stability: CaseResult['stability'];
  worst: boolean;
}

export interface PresentedFlakiness {
  headline: string;
  detail: string;
  rows: FlakyRow[];
  severity: 'none' | 'medium';
  action: 'run-again' | 'none';
}

const ORDER: Record<CaseResult['stability'], number> = { flaky: 0, unknown: 1, steady: 2 };

export function presentFlakiness(state: FlakinessState): PresentedFlakiness {
  const rows = Object.entries(state.cases)
    // Steady cases need nothing; listing them buries the ones that do.
    .filter(([, result]) => result.stability !== 'steady')
    .sort(([, a], [, b]) => ORDER[a.stability] - ORDER[b.stability])
    .map(([caseId, result]) => ({
      caseId,
      description: result.reason,
      stability: result.stability,
      worst: caseId === state.worst,
    }));

  return {
    headline: state.mayGate ? 'This suite is steady' : 'This suite cannot decide releases yet',
    detail:
      state.flakyShare > 0 ? `${Math.round(state.flakyShare * 100)}% of cases are unreliable` : '',
    rows,
    severity: state.mayGate ? 'none' : 'medium',
    action: state.mayGate ? 'none' : 'run-again',
  };
}

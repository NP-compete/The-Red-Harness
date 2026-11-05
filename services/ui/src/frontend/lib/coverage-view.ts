export interface CoverageState {
  complete: boolean;
  uncovered: string[];
  unused: number[];
  share: number;
  reason: string;
  partCount: number;
}

export interface PresentedCoverage {
  /** Catalogue keys, not words: this runs where there is no
   *  translator. The counts beside them drive the plurals. */
  headline: string;
  headlineCount: number;
  parts: string[];
  covered: string;
  coveredPercent: number;
  note: string;
  noteCount: number;
  severity: 'medium' | 'high';
  action: 'ask-separately' | 'reword';
}

export function presentCoverage(state: CoverageState): PresentedCoverage | null {
  if (state.complete) return null;

  const nothing = state.share === 0;
  const missing = state.uncovered.length;
  const spare = state.unused.length;

  return {
    headline: nothing ? 'coverage.nothingFound' : 'coverage.unanswered',
    headlineCount: missing,
    parts: state.uncovered,
    covered: 'coverage.covered',
    coveredPercent: Math.round(state.share * 100),
    // Material that fits nothing asked usually means the search drifted.
    note: spare > 0 ? 'coverage.spare' : '',
    noteCount: spare,
    severity: nothing ? 'high' : 'medium',
    action: nothing ? 'reword' : 'ask-separately',
  };
}

export interface AgreementState {
  agreement: number;
  trust: 'reliable' | 'unreliable' | 'unknown';
  bias: string;
  tooGenerous: number;
  tooHarsh: number;
  disagreements: string[];
  mayGate: boolean;
  reason: string;
  comparisons: number;
}

export interface PresentedAgreement {
  headline: string;
  status: string;
  detail: string;
  biasNote: string;
  openCases: string[];
  severity: 'none' | 'medium';
  action: 'review-disagreements' | 'compare-more';
}

export function presentAgreement(state: AgreementState): PresentedAgreement {
  const unknown = state.trust === 'unknown';

  return {
    headline: `Agrees with people ${Math.round(state.agreement * 100)}% of the time`,
    status: unknown
      ? 'Not enough comparisons yet'
      : state.mayGate
        ? 'Reliable enough to gate releases'
        : 'Not reliable enough to gate releases',
    detail: unknown ? state.reason : '',
    biasNote: biasNote(state),
    openCases: state.disagreements,
    severity: state.trust === 'unreliable' ? 'medium' : 'none',
    action: unknown ? 'compare-more' : 'review-disagreements',
  };
}

function biasNote(state: AgreementState): string {
  // Direction matters more than the rate: the two failures cost different things.
  if (state.bias === 'too generous') {
    return `It passes things people would fail (${state.tooGenerous} times)`;
  }
  if (state.bias === 'too harsh') {
    return `It fails things people would pass (${state.tooHarsh} times)`;
  }
  return '';
}

export interface GateDecision {
  release: boolean;
  blockers: string[];
  exceptional: boolean;
  reason: string;
  nextStep: string;
}

export interface PresentedGate {
  headline: string;
  detail: string;
  reasons: string[];
  nextStep: string;
  note: string;
  blockerCount: number;
  canRelease: boolean;
  override: false;
  severity: 'none' | 'medium' | 'high';
}

const WORDS: Record<string, string> = {
  regressed: 'Something that worked has stopped working',
  'unreliable-suite': 'The test suite does not agree with itself',
  'unproven-judge': 'The automatic judge has not been checked against people enough',
  'weak-dataset': 'There are too few cases to tell a real change from noise',
  'budget-spent': 'The error budget is spent',
};

export function presentGate(decision: GateDecision): PresentedGate {
  return {
    headline: decision.release ? 'Ready to release' : 'Not ready to release',
    detail: decision.reason,
    reasons: decision.blockers.map((blocker) => WORDS[blocker] ?? blocker),
    nextStep: decision.nextStep,
    note: decision.exceptional ? 'Released while the error budget was spent' : '',
    blockerCount: decision.blockers.length,
    canRelease: decision.release,
    // No button exists for going round a blocker; the signals have to change.
    override: false,
    severity: !decision.release ? 'high' : decision.exceptional ? 'medium' : 'none',
  };
}

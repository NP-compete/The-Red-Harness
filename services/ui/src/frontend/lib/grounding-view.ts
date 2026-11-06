export interface CheckedClaim {
  text: string;
  supported: boolean;
  supportedBy: string;
  reason: string;
}

export interface GroundingState {
  grounded: boolean;
  supportedShare: number;
  unsupported: string[];
  contradicted?: string[];
  claims: CheckedClaim[];
  reason: string;
}

export interface PresentedGrounding {
  headline: string;
  detail: string;
  parts: string[];
  contradictions: string[];
  verified: false;
  severity: 'medium' | 'high';
  action: 'show-sources';
}

export function presentGrounding(state: GroundingState): PresentedGrounding | null {
  if (state.grounded) return null;

  const contradictions = state.contradicted ?? [];
  // A contradiction is already counted as unsupported; it is not two faults.
  const missing = state.unsupported.filter((part) => !contradictions.includes(part));
  const count = missing.length;
  const nothingChecked = count === 0 && contradictions.length === 0;

  return {
    headline: headline(contradictions.length, count, nothingChecked),
    detail: nothingChecked
      ? state.reason
      : `${Math.round(state.supportedShare * 100)}% of this answer is backed by a source`,
    parts: missing,
    contradictions,
    // Shown only when something is wrong, so it never doubles as a tick of approval.
    verified: false,
    // Saying the reverse of the source is serious whatever the rest scores.
    severity:
      contradictions.length > 0 || state.supportedShare === 0 ? 'high' : 'medium',
    action: 'show-sources',
  };
}

function headline(contradictions: number, missing: number, nothingChecked: boolean): string {
  if (nothingChecked) return 'This answer could not be checked';
  if (contradictions > 0) {
    return `${contradictions} part${contradictions === 1 ? ' of this answer contradicts its source' : 's of this answer contradict their sources'}`;
  }
  return `${missing} part${missing === 1 ? ' of this answer is' : 's of this answer are'} not backed by a source`;
}

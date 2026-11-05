export type ScopeRefusal = 'wrong-org' | 'wrong-team' | 'not-owner' | null;

export interface ScopeDecision {
  permitted: boolean;
  refusal: ScopeRefusal;
  reason: string;
}

export interface PresentedScopeRefusal {
  headline: string;
  detail: string;
  severity: 'none' | 'low';
  action: 'request-access' | 'none';
}

export function presentScopeRefusal(
  decision: ScopeDecision,
): PresentedScopeRefusal | null {
  if (decision.permitted) return null;

  // Across organisations the answer is the same as for something that is not
  // there; anything richer confirms the item exists.
  if (decision.refusal === 'wrong-org') {
    return { headline: 'Not found', detail: '', severity: 'none', action: 'none' };
  }

  if (decision.refusal === 'wrong-team') {
    return {
      headline: 'This belongs to another team',
      detail: decision.reason,
      severity: 'low',
      action: 'request-access',
    };
  }

  return {
    headline: 'Only the owner can change this',
    detail: decision.reason,
    severity: 'low',
    action: 'none',
  };
}

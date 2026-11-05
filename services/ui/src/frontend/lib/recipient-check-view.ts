export interface RecipientCheckState {
  reaches: number;
  outside: string[];
  unfamiliar: string[];
  reasons: string[];
}

export interface PresentedRecipientCheck {
  headline: string;
  reasons: string[];
  highlight: string[];
  actions: string[];
  blocking: boolean;
  severity: 'medium' | 'high';
}

const CROWD = 20;

export function presentRecipientCheck(
  check: RecipientCheckState,
): PresentedRecipientCheck | null {
  if (check.reasons.length === 0) {
    return null;
  }

  return {
    headline: `This would reach ${check.reaches} ${check.reaches === 1 ? 'person' : 'people'}`,
    reasons: check.reasons,
    highlight: [...new Set([...check.outside, ...check.unfamiliar])],
    // Sending is the irreversible one, so it is never the quiet default.
    actions: ['Send', 'Edit recipients', 'Cancel'],
    blocking: true,
    severity: check.reaches >= CROWD ? 'high' : 'medium',
  };
}

import published from '@/contract/decisions.json';

export type Outcome = 'allowed' | 'needs_approval' | 'refused' | 'unavailable';
export type Code = 'no_authority' | 'policy_denied' | 'budget_exhausted';

export const OUTCOMES: Outcome[] = ['allowed', 'needs_approval', 'refused', 'unavailable'];
export const CODES: Code[] = ['no_authority', 'policy_denied', 'budget_exhausted'];

export function remedyFor(code: Code): string {
  return published.remedies[code];
}

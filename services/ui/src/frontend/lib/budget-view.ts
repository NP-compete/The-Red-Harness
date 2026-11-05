export interface BudgetState {
  /** Tools that had used up their allowance and were taken away. */
  withheld: string[];
  scope: 'block' | 'conversation';
  limit: number;
}

export interface PresentedBudget {
  headline: string;
  detail: string;
  /** The answer still arrived; it was written with less. */
  failed: false;
}

/**
 * What to say about an answer written without a tool.
 *
 * Without this the answer just looks thinner than expected, and the
 * reader has no way to tell a shallow answer from a constrained one.
 */
export function presentBudget(state?: BudgetState | null): PresentedBudget | null {
  if (!state || state.withheld.length === 0) return null;

  return {
    headline: 'This answer was written without a tool',
    // Named, not counted: which tool was missing decides whether the
    // answer is worth asking again for.
    detail: `${state.withheld.join(', ')} had run out of its allowance (${state.limit} per ${state.scope})`,
    failed: false,
  };
}

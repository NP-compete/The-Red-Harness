export interface IncludedPart {
  name: string;
  tokens: number;
  required: boolean;
}

export interface AllocationState {
  included: IncludedPart[];
  dropped: string[];
  usedTokens: number;
  spareTokens: number;
  budgetTokens: number;
  overBudget: boolean;
}

export interface KeptRow {
  name: string;
  required: boolean;
  share: number;
}

export interface PresentedAllocation {
  headline: string;
  usage: string;
  kept: KeptRow[];
  leftOut: string[];
  openByDefault: boolean;
  severity: 'info' | 'high';
  action: 'shorten' | 'none';
}

export function presentAllocation(state: AllocationState): PresentedAllocation | null {
  // Nothing to say when everything the run wanted was carried.
  if (state.dropped.length === 0 && !state.overBudget) return null;

  const count = state.dropped.length;

  return {
    headline: state.overBudget
      ? 'This does not fit in the context window'
      : `${count} thing${count === 1 ? ' was' : 's were'} left out for space`,
    usage: `${state.usedTokens} of ${state.budgetTokens} tokens`,
    kept: state.included.map((part) => ({
      name: part.name,
      required: part.required,
      share: state.budgetTokens > 0 ? part.tokens / state.budgetTokens : 0,
    })),
    leftOut: state.dropped,
    // Routine trimming stays out of the way; not fitting at all does not.
    openByDefault: state.overBudget,
    severity: state.overBudget ? 'high' : 'info',
    action: state.overBudget ? 'shorten' : 'none',
  };
}

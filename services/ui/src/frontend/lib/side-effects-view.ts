export interface EffectsState {
  count: number;
  changedAnything: boolean;
  byKind: Record<string, string[]>;
  permanent: string[];
  fullyReversible: boolean;
  undoSteps: string[];
  cost: string;
  currency: string;
  summary: string;
}

export interface EffectGroup {
  label: string;
  targets: string[];
}

export interface PresentedSideEffects {
  headline: string;
  groups: EffectGroup[];
  permanent: string[];
  undoNote: string;
  undoSteps: string[];
  cost: string;
  severity: 'info' | 'medium';
  action: 'undo' | 'none';
}

export function presentSideEffects(state: EffectsState): PresentedSideEffects {
  const amount = Number(state.cost);

  return {
    headline: state.summary,
    groups: Object.entries(state.byKind)
      .sort((a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0]))
      .map(([kind, targets]) => ({ label: label(kind), targets })),
    permanent: state.permanent,
    undoNote: state.fullyReversible ? '' : 'Some of this cannot be undone',
    // The steps are shown even when the button is not offered: partial undo
    // is still worth doing by hand.
    undoSteps: state.undoSteps,
    cost: amount > 0 ? money(amount, state.currency) : '',
    severity: state.fullyReversible ? 'info' : 'medium',
    action: state.fullyReversible && state.changedAnything ? 'undo' : 'none',
  };
}

function label(kind: string): string {
  // A heading names the category, so it stays plural whatever the count.
  const [noun, verb] = kind.split('-');
  return `${noun.charAt(0).toUpperCase()}${noun.slice(1)}s ${verb}`;
}

function money(amount: number, currency: string): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(amount);
}

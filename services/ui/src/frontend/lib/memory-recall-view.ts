export interface RecalledMemory {
  key: string;
  text: string;
  because: string;
}

export interface RecallState {
  recalled: RecalledMemory[];
  leftOut: string[];
  words: number;
  budgetWords: number;
}

export interface RecallRow {
  key: string;
  text: string;
  because: string;
  pinned: boolean;
  action: 'forget';
}

export interface PresentedRecall {
  headline: string;
  rows: RecallRow[];
  note: string;
  usage: string;
  openByDefault: boolean;
}

const PINNED = 'pinned';

export function presentRecall(state: RecallState): PresentedRecall | null {
  if (state.recalled.length === 0) return null;

  const count = state.recalled.length;
  const missed = state.leftOut.length;

  return {
    headline: `Using ${count} thing${count === 1 ? '' : 's'} it remembers about you`,
    rows: state.recalled.map((memory) => ({
      key: memory.key,
      text: memory.text,
      because:
        memory.because === PINNED ? 'always included' : `because you mentioned ${memory.because}`,
      pinned: memory.because === PINNED,
      // Correcting what it remembers belongs where the memory is shown.
      action: 'forget' as const,
    })),
    note: missed > 0 ? `${missed} other memor${missed === 1 ? 'y' : 'ies'} did not fit` : '',
    usage: `${state.words} of ${state.budgetWords} words`,
    // Background, not an announcement; it waits to be opened.
    openByDefault: false,
  };
}

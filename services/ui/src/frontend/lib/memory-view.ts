export interface RememberedFact {
  text: string;
  sourceThread: string;
  sourceTitle?: string;
  notedAt: string;
}

export interface MemoryRow {
  text: string;
  source: string;
  notedAt: string;
  actions: ['forget'];
}

export interface PresentedMemory {
  rows: MemoryRow[];
  count: number;
  emptyMessage: string;
  bulkAction?: 'forget-all';
}

const EMPTY = 'Nothing is remembered about you yet.';

export function presentMemory(facts: RememberedFact[]): PresentedMemory {
  const rows = [...facts]
    .sort((a, b) => b.notedAt.localeCompare(a.notedAt))
    .map<MemoryRow>((fact) => ({
      text: fact.text,
      // Where it was learned is what makes a wrong memory checkable.
      source: fact.sourceTitle ?? fact.sourceThread,
      notedAt: fact.notedAt,
      actions: ['forget'],
    }));

  return {
    rows,
    count: rows.length,
    emptyMessage: EMPTY,
    bulkAction: rows.length > 0 ? 'forget-all' : undefined,
  };
}

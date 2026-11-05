export interface DiffEntry {
  key: string;
  kind: 'changed' | 'added' | 'removed';
  before: string;
  after: string;
  loosens: boolean;
}

export interface DiffState {
  changes: DiffEntry[];
  count: number;
  loosens: boolean;
  summary: string;
}

export interface DiffRow {
  key: string;
  description: string;
  needsAttention: boolean;
}

export interface PresentedDiff {
  headline: string;
  rows: DiffRow[];
  warning: string;
  needsReview: boolean;
}

export function presentDiff(diff: DiffState): PresentedDiff | null {
  if (diff.changes.length === 0) return null;

  const loosened = diff.changes.filter((change) => change.loosens).length;

  return {
    headline: diff.summary,
    rows: [...diff.changes]
      // What gives more freedom is read first, whatever order it was written in.
      .sort((a, b) => Number(b.loosens) - Number(a.loosens) || a.key.localeCompare(b.key))
      .map((change) => ({
        key: change.key,
        description: describe(change),
        needsAttention: change.loosens,
      })),
    warning:
      loosened > 0
        ? `${loosened} of these give${loosened === 1 ? 's' : ''} more freedom than before`
        : '',
    needsReview: diff.loosens,
  };
}

function describe(change: DiffEntry): string {
  if (change.kind === 'removed') return `${change.key}: ${change.before} removed`;
  if (change.kind === 'added') return `${change.key}: ${change.after} added`;
  return `${change.key}: ${change.before} → ${change.after}`;
}

export type EditOutcome = 'applied' | 'merged' | 'conflict' | 'no-change' | 'unknown-version';

export interface EditResult {
  outcome: EditOutcome;
  version: number;
  reason: string;
  disputed: string[];
  otherAuthor: string;
}

export interface PresentedEdit {
  headline: string;
  severity: 'none' | 'low' | 'high';
  action: 'compare' | 'reload' | 'none';
  keepDraft: boolean;
}

export function presentEditOutcome(result: EditResult): PresentedEdit {
  switch (result.outcome) {
    case 'conflict':
      return {
        headline: `Not saved — ${result.otherAuthor} changed ${list(result.disputed)} first`,
        severity: 'high',
        // Overwriting is never the first offer; the other change has to be seen.
        action: 'compare',
        keepDraft: true,
      };
    case 'unknown-version':
      return {
        headline: 'This page is out of date — reload before saving',
        severity: 'high',
        action: 'reload',
        keepDraft: true,
      };
    case 'merged':
      return {
        headline: `Saved alongside changes from ${result.otherAuthor}`,
        severity: 'low',
        action: 'none',
        keepDraft: false,
      };
    case 'no-change':
      return { headline: 'Nothing to save', severity: 'none', action: 'none', keepDraft: false };
    default:
      return { headline: 'Saved', severity: 'none', action: 'none', keepDraft: false };
  }
}

function list(names: string[]): string {
  if (names.length <= 1) return names[0] ?? 'a setting';
  return `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`;
}

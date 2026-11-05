export interface IndexState {
  state: 'in-step' | 'behind' | 'needs-tidying' | 'broken';
  missing: string[];
  orphaned: string[];
  failed: string[];
  coverage: number;
  trustworthy: boolean;
}

export interface PresentedIndexHealth {
  headline: string;
  warning: string;
  coverage: string;
  documents: string[];
  severity: 'info' | 'medium' | 'high';
  action: 'index-now' | 'view-errors' | 'tidy';
}

export function presentIndexHealth(state: IndexState): PresentedIndexHealth | null {
  if (state.state === 'in-step') return null;

  const { headline, documents, action, severity } = describe(state);

  return {
    headline,
    // Only said when the gap could change an answer.
    warning: state.trustworthy ? '' : 'Answers may be missing information',
    coverage: `${Math.round(state.coverage * 100)}% searchable`,
    documents,
    severity,
    action,
  };
}

function describe(state: IndexState): {
  headline: string;
  documents: string[];
  action: PresentedIndexHealth['action'];
  severity: PresentedIndexHealth['severity'];
} {
  if (state.state === 'broken') {
    return {
      headline: `${count(state.failed)} could not be indexed`,
      documents: state.failed,
      // Retrying something that already failed usually fails the same way.
      action: 'view-errors',
      severity: 'high',
    };
  }

  if (state.state === 'behind') {
    return {
      headline: `${count(state.missing)} ${state.missing.length === 1 ? 'is' : 'are'} not searchable yet`,
      documents: state.missing,
      action: 'index-now',
      severity: 'medium',
    };
  }

  return {
    headline: `${state.orphaned.length} removed document${
      state.orphaned.length === 1 ? ' is' : 's are'
    } still indexed`,
    documents: state.orphaned,
    action: 'tidy',
    severity: 'info',
  };
}

function count(items: string[]): string {
  return `${items.length} document${items.length === 1 ? '' : 's'}`;
}

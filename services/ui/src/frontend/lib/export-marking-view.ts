export interface MarkingState {
  marked: boolean;
  placement: 'footer' | 'none';
  exportId: string;
  format: string;
  classification: string;
}

export interface PresentedMarking {
  headline: string;
  detail: string;
  reference: string;
  warning: string;
  traceableFromFile: boolean;
  severity: 'info' | 'medium';
}

const SENSITIVE = new Set(['confidential', 'restricted']);

export function presentMarking(state: MarkingState): PresentedMarking {
  const sensitive = SENSITIVE.has(state.classification);

  return {
    headline: state.marked ? 'This file is marked' : 'This file carries no mark',
    detail: state.marked
      ? 'A note at the end records where this came from'
      : 'The export is still recorded against your account',
    // Quotable either way: the record exists even when the file cannot hold it.
    reference: state.exportId,
    warning: sensitive
      ? `This is ${state.classification} — do not share it outside your organisation`
      : '',
    traceableFromFile: state.marked,
    severity: sensitive ? 'medium' : 'info',
  };
}

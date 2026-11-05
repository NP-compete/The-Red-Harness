export type ImportVerdict = 'accept' | 'hold' | 'refuse';

export interface ImportState {
  verdict: ImportVerdict;
  reason: string;
  rowsTaken: number;
  trusted: boolean;
}

export interface PresentedImport {
  headline: string;
  detail: string;
  provenance: string;
  actions: string[];
  severity: 'info' | 'medium' | 'high';
}

const HEADLINE: Record<ImportVerdict, (rows: number) => string> = {
  accept: (rows) => `Ready to import ${rows} rows`,
  hold: () => 'This file needs approval first',
  refuse: () => 'This file cannot be imported',
};

const ACTIONS: Record<ImportVerdict, string[]> = {
  accept: ['Import', 'Cancel'],
  hold: ['Request approval', 'Cancel'],
  refuse: ['Cancel'],
};

const SEVERITY: Record<ImportVerdict, PresentedImport['severity']> = {
  accept: 'info',
  hold: 'medium',
  refuse: 'high',
};

export function presentImport(state: ImportState): PresentedImport {
  return {
    headline: HEADLINE[state.verdict](state.rowsTaken),
    detail: state.reason,
    // Where the data came from follows it, whatever was decided about it.
    provenance: state.trusted ? '' : 'From outside — treated as unverified',
    actions: ACTIONS[state.verdict],
    severity: SEVERITY[state.verdict],
  };
}

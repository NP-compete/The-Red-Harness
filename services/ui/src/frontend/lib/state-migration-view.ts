export interface MigrationState {
  outcome: 'already-current' | 'migrated' | 'too-new' | 'no-path';
  applied: number[];
  reason: string;
  storedVersion: number;
  appVersion: number;
}

export interface PresentedMigration {
  headline: string;
  detail: string;
  readOnly: boolean;
  severity: 'medium' | 'high';
  action: 'export' | 'none';
}

export function presentMigration(state: MigrationState): PresentedMigration | null {
  // A successful upgrade is not news; only the cases that limit what the
  // reader can do are worth saying.
  if (state.outcome === 'already-current' || state.outcome === 'migrated') return null;

  if (state.outcome === 'too-new') {
    return {
      headline: 'This conversation is from a newer version',
      detail: 'It is shown as it was saved, and cannot be changed here',
      readOnly: true,
      severity: 'medium',
      action: 'none',
    };
  }

  return {
    headline: 'This conversation cannot be opened',
    detail: state.reason,
    readOnly: true,
    severity: 'high',
    // The content is still there, even if this version cannot read it properly.
    action: 'export',
  };
}

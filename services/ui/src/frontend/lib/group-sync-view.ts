export interface SyncResult {
  person: string;
  teams: string[];
  roles: string[];
  unmapped: string[];
  changed: boolean;
  removedAll: boolean;
  reason: string;
}

export interface SyncRow {
  person: string;
  summary: string;
  attention: boolean;
}

export interface PresentedSync {
  rows: SyncRow[];
  changedCount: number;
  unmappedGroups: string[];
  skipped: string[];
  emptyMessage: string;
}

export function presentSyncResults(results: SyncResult[]): PresentedSync {
  const skipped = results.filter((result) => result.reason !== '');
  const acted = results.filter((result) => result.reason === '');

  const rows = acted
    .filter((result) => result.changed)
    .sort((a, b) => Number(b.removedAll) - Number(a.removedAll) || a.person.localeCompare(b.person))
    .map((result) => ({
      person: result.person,
      summary: result.removedAll ? 'loses all access' : [...result.teams, ...result.roles].join(', '),
      attention: result.removedAll,
    }));

  const unmappedGroups = [...new Set(results.flatMap((result) => result.unmapped))].sort();

  return {
    rows,
    changedCount: rows.length,
    unmappedGroups,
    // A person the sync could not act on is a gap, not a non-event.
    skipped: skipped.map((result) => result.person),
    emptyMessage: rows.length === 0 ? 'No access changes' : '',
  };
}

export interface Revision {
  version: number;
  author: string;
  at: string;
  /**
   * Which settings this revision touched.
   *
   * Optional, because a history of one path is already about
   * that path and naming it on every row is noise.
   */
  changed?: string[];
}

export interface HistoryRow {
  version: number;
  by: string;
  summary: string;
  current: boolean;
  canRestore: boolean;
  note: string;
}

export interface PresentedHistory {
  rows: HistoryRow[];
  count: number;
  restoreNote: string;
  emptyMessage: string;
}

export function presentHistory(revisions: Revision[], now: Date): PresentedHistory {
  const ordered = [...revisions].sort((a, b) => b.version - a.version);
  const currentVersion = ordered[0]?.version;

  const rows = ordered.map((revision) => {
    const current = revision.version === currentVersion;

    return {
      version: revision.version,
      by: `${revision.author}, ${ago(revision.at, now)}`,
      // Only when there is something to say. A history of one
      // path is already about that path.
      summary: revision.changed?.length ? `changed ${list(revision.changed)}` : '',
      current,
      // Anything that is not already in force. There was a
      // thirty-day cutoff here and the agent has no such rule,
      // so it hid a button while the capability remained and
      // the rule was findable nowhere.
      canRestore: !current,
      note: '',
    };
  });

  return {
    rows,
    count: rows.length,
    // Restoring is forward motion, not an erasure, and the wording says so.
    restoreNote: 'Restoring adds a new revision; nothing is erased',
    emptyMessage: rows.length === 0 ? 'No changes recorded' : '',
  };
}

function list(names: string[]): string {
  if (names.length <= 1) return names[0] ?? 'nothing';
  return `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`;
}

function ago(at: string, now: Date): string {
  const hours = Math.round((now.getTime() - Date.parse(at)) / 3_600_000);
  if (hours < 1) return 'just now';
  if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} ago`;
  const days = Math.round(hours / 24);
  return `${days} day${days === 1 ? '' : 's'} ago`;
}

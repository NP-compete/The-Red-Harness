export interface WatchItem {
  document: string;
  summary: string;
  deleted: boolean;
}

export interface PresentedWatchDigest {
  headline: string;
  lines: string[];
  actions: string[];
  blocking: boolean;
  severity: 'info' | 'medium';
}

export function presentWatchDigest(items: WatchItem[]): PresentedWatchDigest | null {
  if (items.length === 0) {
    return null;
  }

  const deletions = items.filter((item) => item.deleted);
  // A deletion cannot be caught up on by reading, so it leads.
  const ordered = [...deletions, ...items.filter((item) => !item.deleted)];

  return {
    headline: `${items.length} source${items.length === 1 ? '' : 's'} you follow changed`,
    lines: ordered.map((item) => item.summary),
    actions: ['Stop following'],
    blocking: false,
    severity: deletions.length > 0 ? 'medium' : 'info',
  };
}

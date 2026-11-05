export interface SourceFreshness {
  name: string;
  state: 'current' | 'behind' | 'stale' | 'unreachable';
  citable: boolean;
  caveat: string;
  dueAt: string | null;
}

export interface PresentedFreshness {
  label: string;
  detail: string;
  due: string;
  severity: 'low' | 'medium' | 'high';
  showBesideCitations: boolean;
  action: 'refresh' | 'reconnect';
}

const LABELS = {
  behind: 'May be out of date',
  stale: 'Not checked recently',
  unreachable: 'Cannot be checked',
} as const;

const SEVERITY = {
  behind: 'medium',
  stale: 'low',
  unreachable: 'high',
} as const;

const DAY = 86_400_000;

export function presentFreshness(
  source: SourceFreshness,
  now: Date,
): PresentedFreshness | null {
  if (source.state === 'current') return null;

  return {
    label: LABELS[source.state],
    detail: source.caveat,
    due: due(source.dueAt, now),
    severity: SEVERITY[source.state],
    // Age alone is routine; a known mismatch belongs next to the claim it supports.
    showBesideCitations: source.state !== 'stale',
    action: source.state === 'unreachable' ? 'reconnect' : 'refresh',
  };
}

function due(at: string | null, now: Date): string {
  if (at === null) return '';
  const days = Math.round((Date.parse(at) - now.getTime()) / DAY);
  if (days <= 0) return 'overdue';
  return `due in ${days} day${days === 1 ? '' : 's'}`;
}

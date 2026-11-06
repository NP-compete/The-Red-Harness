export interface RetentionState {
  action: 'keep' | 'archive' | 'delete';
  deleteOn: string | null;
  warn: boolean;
  reason: string;
  pinned: boolean;
  onLegalHold: boolean;
}

export interface PresentedRetention {
  label: string;
  urgent: boolean;
  canDeleteNow: boolean;
  action: 'pin' | 'unpin' | 'none';
}

const DAY = 86_400_000;

export function presentRetention(state: RetentionState, now: Date): PresentedRetention {
  return {
    label: label(state, now),
    urgent: state.warn,
    canDeleteNow: !state.onLegalHold,
    action: state.onLegalHold ? 'none' : state.pinned ? 'unpin' : 'pin',
  };
}

function label(state: RetentionState, now: Date): string {
  if (state.onLegalHold) return 'Kept while on legal hold';
  if (state.pinned && !state.deleteOn) return 'Kept because it is pinned';
  if (!state.deleteOn) return 'Kept indefinitely';

  const phrase = state.warn ? countdown(state.deleteOn, now) : `deletes on ${date(state.deleteOn)}`;
  if (state.action === 'archive') return `Archived, ${phrase}`;
  return phrase.charAt(0).toUpperCase() + phrase.slice(1);
}

function countdown(deleteOn: string, now: Date): string {
  const days = Math.floor((new Date(deleteOn).getTime() - now.getTime()) / DAY);
  if (days <= 0) return 'deletes today';
  return `deletes in ${days} day${days === 1 ? '' : 's'}`;
}

function date(iso: string): string {
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  });
}

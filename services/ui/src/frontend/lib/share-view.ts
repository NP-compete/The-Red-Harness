export interface ShareState {
  audience: 'signed-in' | 'public';
  expiresAt: string;
  views: number;
  revoked: boolean;
}

export interface PresentedShare {
  audience: string;
  /** Catalogue keys with their counts: this runs where there is no
   *  translator, so a sentence built here would be English in every
   *  language. */
  expiry: string;
  expiryCount: number;
  views: string;
  viewsCount: number;
  active: boolean;
  actions: Array<'revoke'>;
  warning?: string;
}

const HOUR = 1000 * 60 * 60;
const AUDIENCES = {
  'signed-in': 'Anyone signed in',
  public: 'Anyone with the link',
} as const;

export function presentShare(share: ShareState, now: Date): PresentedShare {
  const hoursLeft = (new Date(share.expiresAt).getTime() - now.getTime()) / HOUR;
  const expired = hoursLeft <= 0;
  const active = !share.revoked && !expired;

  return {
    audience: AUDIENCES[share.audience],
    expiry: expired ? 'share.expired' : describe(hoursLeft).key,
    expiryCount: expired ? 0 : describe(hoursLeft).count,
    views: describeViews(share.views),
    viewsCount: share.views,
    active,
    actions: active ? ['revoke'] : [],
    // A link anybody can open is the one worth a second look before it
    // quietly lapses or keeps working.
    warning:
      active && share.audience === 'public' && hoursLeft <= 24
        ? 'share.publicSoon'
        : undefined,
  };
}

/** Which key says how long is left, and the number it counts. */
function describe(hoursLeft: number): { key: string; count: number } {
  if (hoursLeft >= 24) {
    return { key: 'share.inDays', count: Math.round(hoursLeft / 24) };
  }
  return { key: 'share.inHours', count: Math.round(hoursLeft) };
}

function describeViews(views: number): string {
  if (views === 0) return 'share.notOpened';
  // "Opened once" reads better than "opened 1 time", and is its own
  // key rather than a special case inside the plural.
  if (views === 1) return 'share.openedOnce';
  return 'share.openedTimes';
}

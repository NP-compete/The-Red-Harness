export interface StoredToken {
  id: string;
  name: string;
  hint: string;
  scopes: string[];
  createdAt: string;
  expiresAt: string;
  lastUsedAt: string | null;
  revokedAt: string | null;
}

export interface TokenRow {
  id: string;
  name: string;
  display: string;
  permissions: string;
  expires: string;
  powerful: boolean;
  neverUsed: boolean;
  note: string;
  action: 'revoke' | 'none';
}

export interface PresentedTokens {
  rows: TokenRow[];
  emptyMessage: string;
}

export interface PresentedNewToken {
  secret: string;
  warning: string;
  action: 'copy';
}

const SOON_DAYS = 14;
const DAY = 86_400_000;

export function presentNewToken(secret: string): PresentedNewToken {
  return {
    secret,
    warning: 'Copy this now — it will not be shown again',
    action: 'copy',
  };
}

export function presentTokens(tokens: StoredToken[], now: Date): PresentedTokens {
  const rows = tokens
    .map((token) => {
      const days = (Date.parse(token.expiresAt) - now.getTime()) / DAY;
      const revoked = token.revokedAt !== null;
      const neverUsed = token.lastUsedAt === null && !revoked;
      const powerful = token.scopes.some((scope) => scope.endsWith('.write'));

      return {
        id: token.id,
        name: token.name,
        // Only enough to tell two tokens apart, never enough to use one.
        display: `${token.hint}…`,
        permissions: describe(token.scopes),
        expires: revoked ? 'revoked' : expiry(days),
        powerful,
        neverUsed,
        note: neverUsed ? 'Never used — remove it?' : '',
        action: revoked ? ('none' as const) : ('revoke' as const),
        _attention: Number(neverUsed) + Number(days <= SOON_DAYS && !revoked),
      };
    })
    .sort((a, b) => b._attention - a._attention || a.name.localeCompare(b.name))
    .map(({ _attention, ...row }) => row);

  return { rows, emptyMessage: rows.length === 0 ? 'No tokens yet' : '' };
}

function describe(scopes: string[]): string {
  const write = scopes.some((scope) => scope.endsWith('.write'));
  const subject = scopes[0]?.split('.')[0] ?? 'nothing';
  return write ? `read and write ${subject}` : `read ${subject}`;
}

function expiry(days: number): string {
  if (days <= 0) return 'expired';
  if (days <= SOON_DAYS) {
    const whole = Math.round(days);
    return `expires in ${whole} day${whole === 1 ? '' : 's'}`;
  }
  return `expires in ${Math.round(days / 7)} weeks`;
}

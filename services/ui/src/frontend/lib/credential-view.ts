export interface StoredCredential {
  name: string;
  owner: string;
  shared: boolean;
  scopes: string[];
  usedByTools: string[];
  expiresAt: string;
  lastUsedAt: string | null;
}

export interface CredentialRow {
  name: string;
  scopes: string[];
  usedBy: string;
  unused: boolean;
  expires: string;
  expiringSoon: boolean;
  sharing: string;
  lastUsed: string;
}

export interface PresentedCredentials {
  rows: CredentialRow[];
  needingAttention: number;
}

const SOON_DAYS = 14;
const DAY = 86_400_000;

export function presentCredentials(
  credentials: StoredCredential[],
  now: Date,
): PresentedCredentials {
  const rows = credentials
    .map((credential) => {
      const days = (Date.parse(credential.expiresAt) - now.getTime()) / DAY;
      return {
        name: credential.name,
        scopes: credential.scopes,
        usedBy: credential.usedByTools.join(', ') || 'nothing',
        unused: credential.usedByTools.length === 0,
        expires: expiry(credential.expiresAt, days),
        expiringSoon: days <= SOON_DAYS,
        sharing: credential.shared ? 'shared with the team' : 'only you',
        lastUsed: credential.lastUsedAt ? ago(credential.lastUsedAt, now) : 'never used',
      };
    })
    .sort((a, b) => Number(b.expiringSoon) - Number(a.expiringSoon) || a.name.localeCompare(b.name));

  return {
    rows,
    needingAttention: rows.filter((item) => item.expiringSoon).length,
  };
}

function expiry(at: string, days: number): string {
  if (days <= 0) return 'expired';
  if (days <= SOON_DAYS) {
    const whole = Math.round(days);
    return `expires in ${whole} day${whole === 1 ? '' : 's'}`;
  }
  return `expires ${date(at)}`;
}

function ago(at: string, now: Date): string {
  const days = Math.round((now.getTime() - Date.parse(at)) / DAY);
  if (days < 1) return 'today';
  return `${days} day${days === 1 ? '' : 's'} ago`;
}

function date(iso: string): string {
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  });
}

import { describe, expect, it } from 'vitest';

import { presentNewToken, presentTokens } from '@/lib/access-token-view';

const now = new Date('2026-10-27T09:00:00Z');

const tokens = [
  {
    id: 't1',
    name: 'nightly export',
    hint: 'Ab3xY9',
    scopes: ['runs.read'],
    createdAt: '2026-10-01T09:00:00Z',
    expiresAt: '2026-11-01T09:00:00Z',
    lastUsedAt: '2026-10-26T09:00:00Z',
    revokedAt: null as string | null,
  },
  {
    id: 't2',
    name: 'old script',
    hint: 'Zz1qQ7',
    scopes: ['runs.read', 'runs.write'],
    createdAt: '2025-10-01T09:00:00Z',
    expiresAt: '2026-10-29T09:00:00Z',
    lastUsedAt: null,
    revokedAt: null as string | null,
  },
];

describe('presentNewToken', () => {
  it('shows the secret once', () => {
    expect(presentNewToken('super-secret-value').secret).toBe('super-secret-value');
  });

  it('says it will not be shown again', () => {
    expect(presentNewToken('x').warning).toBe('Copy this now — it will not be shown again');
  });

  it('offers to copy it', () => {
    expect(presentNewToken('x').action).toBe('copy');
  });
});

const row = (id: string) =>
  presentTokens(tokens, now).rows.find((candidate) => candidate.id === id)!;

describe('presentTokens', () => {
  it('never shows a full secret in the list', () => {
    const shown = JSON.stringify(presentTokens(tokens, now));
    expect(shown).not.toContain('super-secret-value');
  });

  it('shows a recognisable hint rather than the whole token', () => {
    expect(row('t1').display).toBe('Ab3xY9…');
  });

  it('says what each token may do', () => {
    expect(row('t2').permissions).toBe('read and write runs');
  });

  it('describes a read-only token plainly', () => {
    expect(row('t1').permissions).toBe('read runs');
  });

  it('warns about a token that can write', () => {
    expect(row('t2').powerful).toBe(true);
  });

  it('does not warn about a read-only token', () => {
    expect(row('t1').powerful).toBe(false);
  });

  it('says when a token expires soon', () => {
    expect(row('t2').expires).toBe('expires in 2 days');
  });

  it('flags a token that has never been used', () => {
    expect(row('t2').neverUsed).toBe(true);
  });

  it('suggests removing a token nobody uses', () => {
    expect(row('t2').note).toBe('Never used — remove it?');
  });

  it('puts tokens needing attention first', () => {
    expect(presentTokens(tokens, now).rows.map((row) => row.id)).toEqual(['t2', 't1']);
  });

  it('lets any token be revoked', () => {
    expect(row('t1').action).toBe('revoke');
  });

  it('shows a revoked token as revoked rather than hiding it', () => {
    const revoked = [{ ...tokens[0], revokedAt: '2026-10-26T09:00:00Z' }];
    expect(presentTokens(revoked, now).rows[0].expires).toBe('revoked');
  });

  it('offers nothing to do with a revoked token', () => {
    const revoked = [{ ...tokens[0], revokedAt: '2026-10-26T09:00:00Z' }];
    expect(presentTokens(revoked, now).rows[0].action).toBe('none');
  });

  it('says plainly when there are no tokens', () => {
    expect(presentTokens([], now).emptyMessage).toBe('No tokens yet');
  });
});

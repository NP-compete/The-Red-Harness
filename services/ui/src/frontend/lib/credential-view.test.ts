import { describe, expect, it } from 'vitest';

import { presentCredentials } from '@/lib/credential-view';

const now = new Date('2026-10-27T09:00:00Z');

const credentials = [
  {
    name: 'mail-token',
    owner: 'ana',
    shared: false,
    scopes: ['mail.send'],
    usedByTools: ['send-email'],
    expiresAt: '2026-12-01T00:00:00Z',
    lastUsedAt: '2026-10-26T09:00:00Z',
  },
  {
    name: 'deploy-key',
    owner: 'team:platform',
    shared: true,
    scopes: ['deploy.write'],
    usedByTools: [],
    expiresAt: '2026-10-29T00:00:00Z',
    lastUsedAt: null,
  },
];

const row = (name: string) =>
  presentCredentials(credentials, now).rows.find((candidate) => candidate.name === name)!;

describe('presentCredentials', () => {
  it('never shows a secret', () => {
    const shown = JSON.stringify(presentCredentials(credentials, now));
    expect(shown).not.toContain('secret');
  });

  it('says which tools use each credential', () => {
    expect(row('mail-token').usedBy).toBe('send-email');
  });

  it('says plainly when nothing uses a credential', () => {
    expect(row('deploy-key').usedBy).toBe('nothing');
  });

  it('flags a credential nothing uses', () => {
    expect(row('deploy-key').unused).toBe(true);
  });

  it('does not flag a credential in use', () => {
    expect(row('mail-token').unused).toBe(false);
  });

  it('says when a distant expiry falls', () => {
    expect(row('mail-token').expires).toBe('expires 1 December 2026');
  });

  it('counts down when expiry is near', () => {
    expect(row('deploy-key').expires).toBe('expires in 2 days');
  });

  it('flags a credential expiring soon', () => {
    expect(row('deploy-key').expiringSoon).toBe(true);
  });

  it('does not flag a distant expiry', () => {
    expect(row('mail-token').expiringSoon).toBe(false);
  });

  it('says plainly when a credential has already expired', () => {
    const expired = [{ ...credentials[0], expiresAt: '2026-10-01T00:00:00Z' }];
    expect(presentCredentials(expired, now).rows[0].expires).toBe('expired');
  });

  it('puts expiring credentials first', () => {
    expect(presentCredentials(credentials, now).rows.map((item) => item.name)).toEqual([
      'deploy-key',
      'mail-token',
    ]);
  });

  it('says a shared credential is shared', () => {
    expect(row('deploy-key').sharing).toBe('shared with the team');
  });

  it('says a personal credential is personal', () => {
    expect(row('mail-token').sharing).toBe('only you');
  });

  it('says when a credential has never been used', () => {
    expect(row('deploy-key').lastUsed).toBe('never used');
  });

  it('says when a credential was last used', () => {
    expect(row('mail-token').lastUsed).toBe('1 day ago');
  });

  it('counts how many need attention', () => {
    expect(presentCredentials(credentials, now).needingAttention).toBe(1);
  });
});

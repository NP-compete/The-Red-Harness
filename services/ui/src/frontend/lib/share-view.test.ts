import { describe, expect, it } from 'vitest';

import { presentShare } from '@/lib/share-view';

import en from '../i18n/locales/en.json';

/**
 * The module returns catalogue keys and the numbers they count: it
 * runs outside a component, where there is no translator. Resolving
 * through English keeps each assertion about what a person reads,
 * and proves the key and its plural forms exist.
 */
function said(key: string, count = 0): string {
  const [section, name] = key.split('.');
  const table = (en as Record<string, Record<string, string>>)[section] ?? {};
  const form = table[`${name}_${count === 1 ? 'one' : 'other'}`] ?? table[name];
  if (form === undefined) throw new Error(`no English string for '${key}'`);
  return form.replace('{{count}}', String(count));
}

const base = {
  audience: 'signed-in' as const,
  expiresAt: '2026-10-28T09:00:00Z',
  views: 3,
  revoked: false,
};

const now = new Date('2026-10-27T09:00:00Z');

describe('presentShare', () => {
  it('says who can see it', () => {
    expect(presentShare(base, now).audience).toBe('Anyone signed in');
  });

  it('describes a public link differently', () => {
    expect(presentShare({ ...base, audience: 'public' }, now).audience).toBe(
      'Anyone with the link',
    );
  });

  it('says when it stops working', () => {
    const a = presentShare(base, now);
    expect(said(a.expiry, a.expiryCount)).toBe('in 1 day');
  });

  it('counts hours when expiry is close', () => {
    const soon = { ...base, expiresAt: '2026-10-27T12:00:00Z' };
    const b = presentShare(soon, now);
    expect(said(b.expiry, b.expiryCount)).toBe('in 3 hours');
  });

  it('says plainly when it has already stopped working', () => {
    const past = { ...base, expiresAt: '2026-10-26T09:00:00Z' };
    const c = presentShare(past, now);
    expect(said(c.expiry, c.expiryCount)).toBe('expired');
  });

  it('marks an expired share as inactive', () => {
    const past = { ...base, expiresAt: '2026-10-26T09:00:00Z' };
    expect(presentShare(past, now).active).toBe(false);
  });

  it('marks a revoked share as inactive whatever its date', () => {
    expect(presentShare({ ...base, revoked: true }, now).active).toBe(false);
  });

  it('warns when a public link is close to expiring and still live', () => {
    const soon = { ...base, audience: 'public' as const, expiresAt: '2026-10-27T10:00:00Z' };
    expect(said(presentShare(soon, now).warning!)).toContain('link');
  });

  it('does not warn about an ordinary signed-in share', () => {
    expect(presentShare(base, now).warning).toBeUndefined();
  });

  it('reports how many times it has been opened', () => {
    const d = presentShare(base, now);
    expect(said(d.views, d.viewsCount)).toBe('opened 3 times');
  });

  it('says nobody has opened it when that is true', () => {
    const e = presentShare({ ...base, views: 0 }, now);
    expect(said(e.views, e.viewsCount)).toBe('not opened yet');
  });

  it('uses the singular for one view', () => {
    const f = presentShare({ ...base, views: 1 }, now);
    expect(said(f.views, f.viewsCount)).toBe('opened once');
  });

  it('offers to revoke a live share', () => {
    expect(presentShare(base, now).actions).toEqual(['revoke']);
  });

  it('offers nothing to revoke once it is dead', () => {
    expect(presentShare({ ...base, revoked: true }, now).actions).toEqual([]);
  });
});

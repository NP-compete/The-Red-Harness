import { describe, expect, it } from 'vitest';

import { presentRateLimit } from '@/lib/rate-limit-view';

import en from '../i18n/locales/en.json';

/**
 * The module returns catalogue keys and a count: it runs outside a
 * component, where there is no translator. The assertions are still
 * about what a person reads, so each key is resolved through English
 * here — which also proves the key and its plural forms exist.
 */
function said(key: string, count: number): string {
  const [section, name] = key.split('.');
  const table = (en as Record<string, Record<string, string>>)[section] ?? {};
  const form = table[`${name}_${count === 1 ? 'one' : 'other'}`] ?? table[name];
  if (form === undefined) throw new Error(`no English string for '${key}'`);
  return form.replace('{{count}}', String(count));
}

const allowed = {
  allowed: true,
  remaining: 3,
  burst: 4,
  retryAfter: 0,
  reason: '',
};

describe('presentRateLimit', () => {
  it('shows nothing while there is plenty of allowance', () => {
    expect(presentRateLimit(allowed)).toBeNull();
  });

  it('warns when the allowance is nearly gone', () => {
    const low = { ...allowed, remaining: 1 };
    const low1 = presentRateLimit(low)!;
    expect(said(low1.headline, low1.count)).toBe('Slow down — 1 request left');
  });

  it('uses the singular for one remaining', () => {
    const one = presentRateLimit({ ...allowed, remaining: 1 })!;
    expect(said(one.headline, one.count)).toContain('1 request left');
  });

  it('says plainly when the allowance is spent', () => {
    const spent = { ...allowed, allowed: false, remaining: 0, retryAfter: 0.5, reason: 'x' };
    const hit = presentRateLimit(spent)!;
    expect(said(hit.headline, hit.count)).toBe('Too many requests');
  });

  it('says how long to wait, rounded up', () => {
    const spent = { ...allowed, allowed: false, remaining: 0, retryAfter: 0.5, reason: 'x' };
    const one = presentRateLimit(spent)!;
    expect(said(one.detail, one.count)).toBe('Try again in 1 second');
  });

  it('uses the plural for a longer wait', () => {
    const spent = { ...allowed, allowed: false, remaining: 0, retryAfter: 4.2, reason: 'x' };
    const many = presentRateLimit(spent)!;
    expect(said(many.detail, many.count)).toBe('Try again in 5 seconds');
  });

  it('treats being blocked as more serious than being warned', () => {
    const spent = { ...allowed, allowed: false, remaining: 0, retryAfter: 1, reason: 'x' };
    expect(presentRateLimit(spent)?.severity).toBe('high');
    expect(presentRateLimit({ ...allowed, remaining: 1 })?.severity).toBe('low');
  });

  it('disables sending while blocked', () => {
    const spent = { ...allowed, allowed: false, remaining: 0, retryAfter: 1, reason: 'x' };
    expect(presentRateLimit(spent)?.canSend).toBe(false);
  });

  it('still allows sending while merely warned', () => {
    expect(presentRateLimit({ ...allowed, remaining: 1 })?.canSend).toBe(true);
  });

  it('says when sending becomes possible again', () => {
    const spent = { ...allowed, allowed: false, remaining: 0, retryAfter: 2, reason: 'x' };
    expect(presentRateLimit(spent)?.retryAfterSeconds).toBe(2);
  });

  it('never suggests retrying immediately when blocked', () => {
    const spent = { ...allowed, allowed: false, remaining: 0, retryAfter: 0.1, reason: 'x' };
    expect(presentRateLimit(spent)?.retryAfterSeconds).toBeGreaterThan(0);
  });

  it('does not blame the person for the limit', () => {
    const spent = { ...allowed, allowed: false, remaining: 0, retryAfter: 1, reason: 'x' };
    const blamed = presentRateLimit(spent)!;
    expect(said(blamed.headline, blamed.count).toLowerCase()).not.toContain('you');
  });
});

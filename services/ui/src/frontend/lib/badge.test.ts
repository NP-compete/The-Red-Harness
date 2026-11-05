import { describe, expect, it } from 'vitest';

import { applyBadge, badgeFor } from '@/lib/badge';

/**
 * The count on the dock icon.
 *
 * It answers one question — how many conversations are stopped
 * waiting for me — so anything that is merely running does not
 * count. A badge that shows activity rather than obligation is a
 * badge people stop looking at.
 */
const threads = [
  { id: 't1', awaitingUser: true },
  { id: 't2', awaitingUser: false },
  { id: 't3', awaitingUser: true },
];

describe('badgeFor', () => {
  it('counts the conversations waiting on somebody', () => {
    expect(badgeFor(threads, { enabled: true }).count).toBe(2);
  });

  it('does not count one that is merely running', () => {
    expect(badgeFor([{ id: 't2', awaitingUser: false }], { enabled: true }).count).toBe(0);
  });

  it('clears once the last one is answered', () => {
    expect(badgeFor([], { enabled: true }).show).toBe(false);
  });

  it('shows while any remain', () => {
    expect(badgeFor(threads, { enabled: true }).show).toBe(true);
  });

  it('shows nothing when the deployment turned the badge off', () => {
    expect(badgeFor(threads, { enabled: false }).show).toBe(false);
  });

  it('reports no count when the badge is off', () => {
    // Not a count of zero: zero is a statement, and the deployment
    // asked for no statement at all.
    expect(badgeFor(threads, { enabled: false }).count).toBe(0);
  });

  it('counts a thread once however many times it appears', () => {
    const repeated = [...threads, { id: 't1', awaitingUser: true }];
    expect(badgeFor(repeated, { enabled: true }).count).toBe(2);
  });

  describe('on a platform the deployment does not support', () => {
    // A badge is notification-shaped. Everything of that shape
    // hides behind the same gate, or the gate has holes in it.
    it('shows nothing', () => {
      expect(badgeFor(threads, { enabled: true, supported: false }).show).toBe(false);
    });

    it('counts nothing', () => {
      expect(badgeFor(threads, { enabled: true, supported: false }).count).toBe(0);
    });

    it('still shows on a supported one', () => {
      expect(badgeFor(threads, { enabled: true, supported: true }).show).toBe(true);
    });

    it('treats an unstated platform as supported, so nothing silently stops', () => {
      // The gate is the caller's to apply; omitting it must not be
      // a quiet way to disable the badge everywhere.
      expect(badgeFor(threads, { enabled: true }).show).toBe(true);
    });
  });
});

describe('putting the count on the icon', () => {
  function navigatorWith(methods: Record<string, unknown>) {
    return methods as unknown as Navigator;
  }

  it('sets the count when something is waiting', () => {
    const setAppBadge = vi.fn();
    applyBadge(navigatorWith({ setAppBadge, clearAppBadge: vi.fn() }), {
      show: true,
      count: 3,
    });
    expect(setAppBadge).toHaveBeenCalledWith(3);
  });

  it('clears rather than setting zero when the last is answered', () => {
    // A zero still paints a mark in some browsers, and a
    // mark that never goes is why people stop reading it.
    const clearAppBadge = vi.fn();
    const setAppBadge = vi.fn();
    applyBadge(navigatorWith({ setAppBadge, clearAppBadge }), { show: false, count: 0 });
    expect(clearAppBadge).toHaveBeenCalled();
    expect(setAppBadge).not.toHaveBeenCalled();
  });

  it('does nothing where the browser has no badging', () => {
    // Most of them. This runs on every state change, so an
    // error here is an error on every turn.
    expect(() => applyBadge(navigatorWith({}), { show: true, count: 2 })).not.toThrow();
  });

  it('survives a browser that can set but not clear', () => {
    expect(() =>
      applyBadge(navigatorWith({ setAppBadge: vi.fn() }), { show: false, count: 0 }),
    ).not.toThrow();
  });

  it('swallows a rejected set', async () => {
    // The call returns a promise and can be refused. Left
    // unhandled it is an unhandled rejection in the console
    // on a feature nobody asked about — and the console is
    // where somebody looks when something else is wrong.
    const setAppBadge = vi.fn().mockRejectedValue(new Error('refused'));
    applyBadge(navigatorWith({ setAppBadge, clearAppBadge: vi.fn() }), {
      show: true,
      count: 1,
    });
    await Promise.resolve();
    expect(setAppBadge).toHaveBeenCalled();
  });

  it('swallows a rejected clear', async () => {
    const clearAppBadge = vi.fn().mockRejectedValue(new Error('refused'));
    applyBadge(navigatorWith({ setAppBadge: vi.fn(), clearAppBadge }), {
      show: false,
      count: 0,
    });
    await Promise.resolve();
    expect(clearAppBadge).toHaveBeenCalled();
  });
});

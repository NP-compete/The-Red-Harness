import { describe, expect, it } from 'vitest';

import { presentPage } from '@/lib/pagination';

const items = Array.from({ length: 25 }, (_, index) => ({
  id: `t${index}`,
  at: `2026-10-27T${String(9 - Math.floor(index / 10)).padStart(2, '0')}:00:00Z`,
}));

describe('presentPage', () => {
  it('shows a first page of the requested size', () => {
    expect(presentPage(items, { loaded: 10 }).visible).toHaveLength(10);
  });

  it('shows the newest first', () => {
    expect(presentPage(items, { loaded: 10 }).visible[0].id).toBe('t0');
  });

  it('says there is more to load', () => {
    expect(presentPage(items, { loaded: 10 }).hasMore).toBe(true);
  });

  it('says how many are not shown', () => {
    expect(presentPage(items, { loaded: 10 }).remaining).toBe(15);
  });

  it('shows everything once enough is loaded', () => {
    expect(presentPage(items, { loaded: 30 }).visible).toHaveLength(25);
  });

  it('stops offering more when everything is shown', () => {
    expect(presentPage(items, { loaded: 30 }).hasMore).toBe(false);
  });

  it('never reports a negative remainder', () => {
    expect(presentPage(items, { loaded: 30 }).remaining).toBe(0);
  });

  it('keeps items already on screen in place when new ones arrive', () => {
    const before = presentPage(items, { loaded: 10 }).visible.map((item) => item.id);
    const withNew = [{ id: 'new', at: '2026-10-27T10:00:00Z' }, ...items];
    const after = presentPage(withNew, { loaded: 10, pinnedTop: 't0' }).visible.map((i) => i.id);
    expect(after).toEqual(before);
  });

  it('reports arrivals above the pinned position separately', () => {
    const withNew = [{ id: 'new', at: '2026-10-27T10:00:00Z' }, ...items];
    expect(presentPage(withNew, { loaded: 10, pinnedTop: 't0' }).newAbove).toBe(1);
  });

  it('reports no arrivals when nothing came in', () => {
    expect(presentPage(items, { loaded: 10, pinnedTop: 't0' }).newAbove).toBe(0);
  });

  it('shows the new items once the pin is released', () => {
    const withNew = [{ id: 'new', at: '2026-10-27T10:00:00Z' }, ...items];
    expect(presentPage(withNew, { loaded: 10 }).visible[0].id).toBe('new');
  });

  it('handles an empty list without inventing a page', () => {
    const shown = presentPage([], { loaded: 10 });
    expect(shown.visible).toEqual([]);
    expect(shown.hasMore).toBe(false);
  });

  it('treats a pin that no longer exists as no pin at all', () => {
    const shown = presentPage(items, { loaded: 10, pinnedTop: 'gone' });
    expect(shown.visible[0].id).toBe('t0');
  });

  it('does not lose items that share a timestamp', () => {
    const tied = [
      { id: 'b', at: '2026-10-27T09:00:00Z' },
      { id: 'a', at: '2026-10-27T09:00:00Z' },
    ];
    expect(presentPage(tied, { loaded: 10 }).visible.map((i) => i.id)).toEqual(['a', 'b']);
  });
});

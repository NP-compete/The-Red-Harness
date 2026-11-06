import { describe, expect, it } from 'vitest';

import { presentFreshness } from '@/lib/freshness-view';

const now = new Date('2026-10-27T09:00:00Z');

const source = {
  name: 'handbook',
  state: 'current' as const,
  citable: true,
  caveat: '',
  dueAt: '2026-11-01T09:00:00Z',
};

describe('presentFreshness', () => {
  it('shows nothing for a source that is up to date', () => {
    expect(presentFreshness(source, now)).toBeNull();
  });

  it('says plainly when the original has changed', () => {
    const behind = {
      ...source,
      state: 'behind' as const,
      caveat: 'the original has changed since this was indexed',
    };
    expect(presentFreshness(behind, now)?.label).toBe('May be out of date');
  });

  it('carries the caveat through for the reader', () => {
    const behind = {
      ...source,
      state: 'behind' as const,
      caveat: 'the original has changed since this was indexed',
    };
    expect(presentFreshness(behind, now)?.detail).toBe(
      'the original has changed since this was indexed',
    );
  });

  it('says plainly when a source is simply old', () => {
    const stale = {
      ...source,
      state: 'stale' as const,
      caveat: 'this was last indexed 10 days ago',
    };
    expect(presentFreshness(stale, now)?.label).toBe('Not checked recently');
  });

  it('says plainly when a source cannot be reached', () => {
    const lost = {
      ...source,
      state: 'unreachable' as const,
      caveat: 'this source has been unreachable for 3 days',
    };
    expect(presentFreshness(lost, now)?.label).toBe('Cannot be checked');
  });

  it('treats an unreachable source as the most serious', () => {
    const lost = { ...source, state: 'unreachable' as const, caveat: 'x' };
    expect(presentFreshness(lost, now)?.severity).toBe('high');
  });

  it('treats being behind as worth noticing', () => {
    const behind = { ...source, state: 'behind' as const, caveat: 'x' };
    expect(presentFreshness(behind, now)?.severity).toBe('medium');
  });

  it('treats being merely old as minor', () => {
    const stale = { ...source, state: 'stale' as const, caveat: 'x' };
    expect(presentFreshness(stale, now)?.severity).toBe('low');
  });

  it('warns beside a citation when the source should not be cited', () => {
    const lost = { ...source, state: 'unreachable' as const, citable: false, caveat: 'x' };
    expect(presentFreshness(lost, now)?.showBesideCitations).toBe(true);
  });

  it('still warns beside citations for a source that is behind', () => {
    const behind = { ...source, state: 'behind' as const, caveat: 'x' };
    expect(presentFreshness(behind, now)?.showBesideCitations).toBe(true);
  });

  it('does not warn beside citations for a merely old source', () => {
    const stale = { ...source, state: 'stale' as const, caveat: 'x' };
    expect(presentFreshness(stale, now)?.showBesideCitations).toBe(false);
  });

  it('offers to refresh a source that can be reached', () => {
    const stale = { ...source, state: 'stale' as const, caveat: 'x' };
    expect(presentFreshness(stale, now)?.action).toBe('refresh');
  });

  it('offers to reconnect one that cannot', () => {
    const lost = { ...source, state: 'unreachable' as const, caveat: 'x' };
    expect(presentFreshness(lost, now)?.action).toBe('reconnect');
  });

  it('says when the next check is due', () => {
    const stale = { ...source, state: 'stale' as const, caveat: 'x' };
    expect(presentFreshness(stale, now)?.due).toBe('due in 5 days');
  });

  it('does not invent a due date for a source with no schedule', () => {
    const stale = { ...source, state: 'stale' as const, caveat: 'x', dueAt: null };
    expect(presentFreshness(stale, now)?.due).toBe('');
  });
});

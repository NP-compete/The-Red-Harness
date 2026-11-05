import { describe, expect, it } from 'vitest';

import { presentPruning } from '@/lib/memory-pruning-view';

const pruning = {
  keptCount: 48,
  capacity: 50,
  dropped: ['old-preference', 'stale-fact'],
  overCapacity: false,
  pinnedCount: 3,
};

describe('presentPruning', () => {
  it('shows nothing when nothing was forgotten', () => {
    expect(presentPruning({ ...pruning, dropped: [] })).toBeNull();
  });

  it('says how many things were forgotten', () => {
    expect(presentPruning(pruning)?.headline).toBe('Forgot 2 things to make room');
  });

  it('uses the singular for one', () => {
    expect(presentPruning({ ...pruning, dropped: ['a'] })?.headline).toBe(
      'Forgot 1 thing to make room',
    );
  });

  it('names what was forgotten so it can be restored', () => {
    expect(presentPruning(pruning)?.forgotten).toEqual(['old-preference', 'stale-fact']);
  });

  it('says how full the memory is', () => {
    expect(presentPruning(pruning)?.usage).toBe('48 of 50 remembered');
  });

  it('says how many are pinned', () => {
    expect(presentPruning(pruning)?.pinnedNote).toBe('3 are pinned and will never be forgotten');
  });

  it('says nothing about pins when there are none', () => {
    expect(presentPruning({ ...pruning, pinnedCount: 0 })?.pinnedNote).toBe('');
  });

  it('warns when pinned items alone exceed the space', () => {
    const full = { ...pruning, overCapacity: true, keptCount: 60, pinnedCount: 60 };
    expect(presentPruning(full)?.warning).toBe(
      'More is pinned than there is room for, so nothing else can be remembered',
    );
  });

  it('does not warn in the ordinary case', () => {
    expect(presentPruning(pruning)?.warning).toBe('');
  });

  it('offers to bring something back', () => {
    expect(presentPruning(pruning)?.action).toBe('restore');
  });

  it('treats being over capacity as worth acting on', () => {
    const full = { ...pruning, overCapacity: true };
    expect(presentPruning(full)?.severity).toBe('medium');
  });

  it('treats ordinary forgetting as routine', () => {
    expect(presentPruning(pruning)?.severity).toBe('info');
  });

  it('can be dismissed', () => {
    expect(presentPruning(pruning)?.dismissible).toBe(true);
  });
});

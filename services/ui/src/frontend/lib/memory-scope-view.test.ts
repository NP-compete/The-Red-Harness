import { describe, expect, it } from 'vitest';

import { presentScope } from '@/lib/memory-scope-view';

const row = {
  key: 'units',
  text: 'Metric units in every report.',
  owner: 'ada',
  ownerIsYou: true,
  team: '',
  sharedWithTeam: false,
  sensitive: false,
  usableHere: true,
};

describe('presentScope', () => {
  it('shows the memory', () => {
    expect(presentScope([row], { sharedThread: false })[0].text).toBe(
      'Metric units in every report.',
    );
  });

  it('calls a memory of your own yours', () => {
    expect(presentScope([row], { sharedThread: false })[0].scope).toBe('Only you');
  });

  it('names the team a memory is shared with', () => {
    const shared = { ...row, team: 'platform', sharedWithTeam: true };
    expect(presentScope([shared], { sharedThread: false })[0].scope).toBe('platform');
  });

  it('says who wrote a memory that is not yours', () => {
    const theirs = { ...row, owner: 'grace', ownerIsYou: false, team: 'platform', sharedWithTeam: true };
    expect(presentScope([theirs], { sharedThread: false })[0].author).toBe('grace');
  });

  it('does not name you as the author of your own memory', () => {
    expect(presentScope([row], { sharedThread: false })[0].author).toBe('');
  });

  it('marks a memory that is being used', () => {
    expect(presentScope([row], { sharedThread: false })[0].inUse).toBe(true);
  });

  it('marks a memory that is being held back', () => {
    const held = { ...row, usableHere: false };
    expect(presentScope([held], { sharedThread: false })[0].inUse).toBe(false);
  });

  it('explains why a memory is held back in a shared thread', () => {
    const held = { ...row, usableHere: false };
    expect(presentScope([held], { sharedThread: true })[0].note).toBe(
      'Not used here — others can read this thread',
    );
  });

  it('explains a held-back memory outside a shared thread differently', () => {
    const held = { ...row, usableHere: false };
    expect(presentScope([held], { sharedThread: false })[0].note).toBe('Not used here');
  });

  it('adds no note to a memory in use', () => {
    expect(presentScope([row], { sharedThread: false })[0].note).toBe('');
  });

  it('flags a sensitive memory so it is not read aloud by accident', () => {
    const private_ = { ...row, sensitive: true };
    expect(presentScope([private_], { sharedThread: false })[0].hidden).toBe(true);
  });

  it('does not hide an ordinary memory', () => {
    expect(presentScope([row], { sharedThread: false })[0].hidden).toBe(false);
  });

  it('puts the memories in use before the ones held back', () => {
    const held = { ...row, key: 'tone', usableHere: false };
    const rows = presentScope([held, row], { sharedThread: false });
    expect(rows.map((r) => r.key)).toEqual(['units', 'tone']);
  });

  it('handles having remembered nothing', () => {
    expect(presentScope([], { sharedThread: false })).toEqual([]);
  });
});

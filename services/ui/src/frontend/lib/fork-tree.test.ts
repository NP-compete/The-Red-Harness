import { describe, expect, it } from 'vitest';

import { presentForkTree } from '@/lib/fork-tree';

const branches = [
  { name: 'main', messages: 12, from: undefined, at: undefined },
  { name: 'no-tracker', messages: 5, from: 'main', at: 'message 4' },
  { name: 'stricter', messages: 7, from: 'main', at: 'message 4' },
];

describe('presentForkTree', () => {
  it('puts the original at the top', () => {
    expect(presentForkTree(branches, { current: 'main' }).rows[0].name).toBe('main');
  });

  it('indents a branch under what it came from', () => {
    const rows = presentForkTree(branches, { current: 'main' }).rows;
    expect(rows.find((row) => row.name === 'no-tracker')?.depth).toBe(1);
  });

  it('keeps the root at the surface', () => {
    const rows = presentForkTree(branches, { current: 'main' }).rows;
    expect(rows[0].depth).toBe(0);
  });

  it('marks where you are', () => {
    const rows = presentForkTree(branches, { current: 'stricter' }).rows;
    expect(rows.find((row) => row.name === 'stricter')?.current).toBe(true);
  });

  it('says where each branch was taken from', () => {
    const rows = presentForkTree(branches, { current: 'main' }).rows;
    expect(rows.find((row) => row.name === 'stricter')?.takenAt).toBe('message 4');
  });

  it('shows how long each branch is', () => {
    const rows = presentForkTree(branches, { current: 'main' }).rows;
    expect(rows[0].messages).toBe(12);
  });

  it('counts the alternatives explored', () => {
    expect(presentForkTree(branches, { current: 'main' }).forkCount).toBe(2);
  });

  it('describes a conversation that was never branched', () => {
    const shown = presentForkTree([branches[0]], { current: 'main' });
    expect(shown.forkCount).toBe(0);
    expect(shown.rows).toHaveLength(1);
  });

  it('nests a branch of a branch deeper', () => {
    const deep = [...branches, { name: 'deeper', messages: 2, from: 'stricter', at: 'message 2' }];
    const rows = presentForkTree(deep, { current: 'main' }).rows;
    expect(rows.find((row) => row.name === 'deeper')?.depth).toBe(2);
  });

  it('still lists a branch whose parent is missing', () => {
    const orphan = [{ name: 'lost', messages: 1, from: 'gone', at: 'message 1' }];
    expect(presentForkTree(orphan, { current: 'lost' }).rows).toHaveLength(1);
  });
});

import { describe, expect, it } from 'vitest';

import { presentDiff } from '@/lib/config-diff-view';

const diff = {
  changes: [
    { key: 'budget', kind: 'changed' as const, before: '100', after: '1000', loosens: true },
    { key: 'model', kind: 'changed' as const, before: 'fast', after: 'careful', loosens: false },
    { key: 'approver', kind: 'removed' as const, before: 'bo', after: '', loosens: true },
  ],
  count: 3,
  loosens: true,
  summary: '2 changed, 1 removed',
};

const row = (key: string) => presentDiff(diff)!.rows.find((item) => item.key === key)!;

describe('presentDiff', () => {
  it('shows nothing when nothing changed', () => {
    const same = { changes: [], count: 0, loosens: false, summary: 'nothing changed' };
    expect(presentDiff(same)).toBeNull();
  });

  it('shows the summary it was given', () => {
    expect(presentDiff(diff)?.headline).toBe('2 changed, 1 removed');
  });

  it('describes a change in plain words', () => {
    expect(row('budget').description).toBe('budget: 100 → 1000');
  });

  it('describes a removal without an arrow to nowhere', () => {
    expect(row('approver').description).toBe('approver: bo removed');
  });

  it('describes an addition plainly', () => {
    const added = {
      ...diff,
      changes: [{ key: 'region', kind: 'added' as const, before: '', after: 'eu-west', loosens: false }],
    };
    expect(presentDiff(added)?.rows[0].description).toBe('region: eu-west added');
  });

  it('puts loosening changes first', () => {
    expect(presentDiff(diff)?.rows.map((row) => row.key)).toEqual([
      'approver',
      'budget',
      'model',
    ]);
  });

  it('marks a loosening change', () => {
    const row = presentDiff(diff)?.rows.find((item) => item.key === 'budget');
    expect(row?.needsAttention).toBe(true);
  });

  it('does not mark an ordinary change', () => {
    const row = presentDiff(diff)?.rows.find((item) => item.key === 'model');
    expect(row?.needsAttention).toBe(false);
  });

  it('warns when anything was loosened', () => {
    expect(presentDiff(diff)?.warning).toBe('2 of these give more freedom than before');
  });

  it('uses the singular for one loosening change', () => {
    const one = { ...diff, changes: [diff.changes[0]], count: 1, summary: '1 changed' };
    expect(presentDiff(one)?.warning).toBe('1 of these gives more freedom than before');
  });

  it('does not warn when everything tightened', () => {
    const tighter = {
      ...diff,
      changes: [{ key: 'budget', kind: 'changed' as const, before: '1000', after: '100', loosens: false }],
      count: 1,
      loosens: false,
      summary: '1 changed',
    };
    expect(presentDiff(tighter)?.warning).toBe('');
  });

  it('asks for review when something was loosened', () => {
    expect(presentDiff(diff)?.needsReview).toBe(true);
  });

  it('does not ask for review when nothing was loosened', () => {
    const tighter = { ...diff, loosens: false, changes: [diff.changes[1]], count: 1 };
    expect(presentDiff(tighter)?.needsReview).toBe(false);
  });
});

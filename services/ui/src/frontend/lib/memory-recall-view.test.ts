import { describe, expect, it } from 'vitest';

import { presentRecall } from '@/lib/memory-recall-view';

const recall = {
  recalled: [
    { key: 'format', text: 'Prefers plain text reports', because: 'report' },
    { key: 'always', text: 'Works in the Berlin office', because: 'pinned' },
  ],
  leftOut: ['timezone'],
  words: 20,
  budgetWords: 100,
};

describe('presentRecall', () => {
  it('shows nothing when nothing was recalled', () => {
    const none = { ...recall, recalled: [], leftOut: [], words: 0 };
    expect(presentRecall(none)).toBeNull();
  });

  it('says how many things it remembered', () => {
    expect(presentRecall(recall)?.headline).toBe('Using 2 things it remembers about you');
  });

  it('uses the singular for one', () => {
    const one = { ...recall, recalled: [recall.recalled[0]] };
    expect(presentRecall(one)?.headline).toBe('Using 1 thing it remembers about you');
  });

  it('shows each memory with why it came up', () => {
    expect(presentRecall(recall)?.rows[0]).toMatchObject({
      key: 'format',
      text: 'Prefers plain text reports',
      because: 'because you mentioned report',
      pinned: false,
    });
  });

  it('describes a pinned memory as always included', () => {
    expect(presentRecall(recall)?.rows[1].because).toBe('always included');
  });

  it('marks a pinned memory', () => {
    expect(presentRecall(recall)?.rows[1].pinned).toBe(true);
  });

  it('says when something was left out for space', () => {
    expect(presentRecall(recall)?.note).toBe('1 other memory did not fit');
  });

  it('uses the plural for several left out', () => {
    const tight = { ...recall, leftOut: ['a', 'b'] };
    expect(presentRecall(tight)?.note).toBe('2 other memories did not fit');
  });

  it('says nothing when everything fitted', () => {
    expect(presentRecall({ ...recall, leftOut: [] })?.note).toBe('');
  });

  it('lets any memory be forgotten from here', () => {
    expect(presentRecall(recall)?.rows[0].action).toBe('forget');
  });

  it('shows how much of the allowance was used', () => {
    expect(presentRecall(recall)?.usage).toBe('20 of 100 words');
  });

  it('is collapsed by default so it does not crowd the conversation', () => {
    expect(presentRecall(recall)?.openByDefault).toBe(false);
  });

  it('stays collapsed even when something was left out', () => {
    expect(presentRecall({ ...recall, leftOut: ['a'] })?.openByDefault).toBe(false);
  });
});

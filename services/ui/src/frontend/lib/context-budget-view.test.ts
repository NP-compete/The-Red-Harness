import { describe, expect, it } from 'vitest';

import { presentAllocation } from '@/lib/context-budget-view';

const full = {
  included: [
    { name: 'instructions', tokens: 100, required: true },
    { name: 'history', tokens: 400, required: false },
  ],
  dropped: [] as string[],
  usedTokens: 500,
  spareTokens: 500,
  budgetTokens: 1000,
  overBudget: false,
};

describe('presentAllocation', () => {
  it('shows nothing when everything fitted', () => {
    expect(presentAllocation(full)).toBeNull();
  });

  it('says plainly when something was left out', () => {
    const trimmed = { ...full, dropped: ['memories'], spareTokens: 0 };
    expect(presentAllocation(trimmed)?.headline).toBe('1 thing was left out for space');
  });

  it('uses the plural for several left out', () => {
    const trimmed = { ...full, dropped: ['memories', 'retrieved'], spareTokens: 0 };
    expect(presentAllocation(trimmed)?.headline).toBe('2 things were left out for space');
  });

  it('names what was left out', () => {
    const trimmed = { ...full, dropped: ['memories'] };
    expect(presentAllocation(trimmed)?.leftOut).toEqual(['memories']);
  });

  it('shows how much of the window was used', () => {
    const trimmed = { ...full, dropped: ['memories'] };
    expect(presentAllocation(trimmed)?.usage).toBe('500 of 1000 tokens');
  });

  it('says plainly when even the essentials did not fit', () => {
    const over = {
      ...full,
      dropped: ['history'],
      usedTokens: 1200,
      spareTokens: 0,
      overBudget: true,
    };
    expect(presentAllocation(over)?.headline).toBe('This does not fit in the context window');
  });

  it('treats not fitting as serious', () => {
    const over = { ...full, dropped: ['history'], overBudget: true };
    expect(presentAllocation(over)?.severity).toBe('high');
  });

  it('treats trimming as routine', () => {
    const trimmed = { ...full, dropped: ['memories'] };
    expect(presentAllocation(trimmed)?.severity).toBe('info');
  });

  it('suggests shortening when it does not fit at all', () => {
    const over = { ...full, dropped: ['history'], overBudget: true };
    expect(presentAllocation(over)?.action).toBe('shorten');
  });

  it('offers nothing to do about ordinary trimming', () => {
    const trimmed = { ...full, dropped: ['memories'] };
    expect(presentAllocation(trimmed)?.action).toBe('none');
  });

  it('marks what had to be kept', () => {
    const trimmed = { ...full, dropped: ['memories'] };
    const kept = presentAllocation(trimmed)?.kept ?? [];
    expect(kept.find((item) => item.name === 'instructions')?.required).toBe(true);
  });

  it('shows what share each part took', () => {
    const trimmed = { ...full, dropped: ['memories'] };
    const kept = presentAllocation(trimmed)?.kept ?? [];
    expect(kept.find((item) => item.name === 'history')?.share).toBeCloseTo(0.4, 2);
  });

  it('is collapsed by default', () => {
    const trimmed = { ...full, dropped: ['memories'] };
    expect(presentAllocation(trimmed)?.openByDefault).toBe(false);
  });

  it('opens itself when nothing fits', () => {
    const over = { ...full, dropped: ['history'], overBudget: true };
    expect(presentAllocation(over)?.openByDefault).toBe(true);
  });
});

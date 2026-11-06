import { describe, expect, it } from 'vitest';

import { presentSpend } from '@/lib/spend';

describe('presentSpend', () => {
  it('shows what a run cost', () => {
    expect(presentSpend({ total: '0.0123', currency: 'USD' }).amount).toBe('$0.0123');
  });

  it('keeps small amounts readable rather than rounding them to nothing', () => {
    expect(presentSpend({ total: '0.0004', currency: 'USD' }).amount).toBe('$0.0004');
  });

  it('shows round amounts to two places', () => {
    expect(presentSpend({ total: '12.5', currency: 'USD' }).amount).toBe('$12.50');
  });

  it('says when part of the spend could not be priced', () => {
    const shown = presentSpend({ total: '1.00', currency: 'USD', unpriced: ['new-model'] });
    expect(shown.note).toContain('new-model');
  });

  it('adds no note when everything was priced', () => {
    expect(presentSpend({ total: '1.00', currency: 'USD' }).note).toBeUndefined();
  });

  it('reports how much of a budget is used', () => {
    const shown = presentSpend({ total: '2.50', currency: 'USD', limit: '10.00' });
    expect(shown.usedPercent).toBe(25);
  });

  it('caps the reported share at a hundred rather than showing more', () => {
    const shown = presentSpend({ total: '15.00', currency: 'USD', limit: '10.00' });
    expect(shown.usedPercent).toBe(100);
    expect(shown.overBudget).toBe(true);
  });

  it('has no share to report without a budget', () => {
    expect(presentSpend({ total: '2.50', currency: 'USD' }).usedPercent).toBeUndefined();
  });

  it('breaks spend down by model, dearest first', () => {
    const shown = presentSpend({
      total: '3.00',
      currency: 'USD',
      byModel: { small: '1.00', large: '2.00' },
    });
    expect(shown.breakdown.map((row) => row.model)).toEqual(['large', 'small']);
  });

  it('separates thousands in token counts', () => {
    expect(presentSpend({ total: '0', currency: 'USD', tokens: 1234567 }).tokens).toBe('1,234,567');
  });
});

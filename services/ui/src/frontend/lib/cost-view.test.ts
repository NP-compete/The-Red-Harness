import { describe, expect, it } from 'vitest';

import { presentCost } from '@/lib/cost-view';

/**
 * Money on a dashboard.
 *
 * Every way of getting this wrong makes the bill look smaller
 * than it is, so each one has to say something rather than
 * quietly rendering a number.
 */
const PRICED = {
  total_cost: '1.334611875',
  currency: 'USD',
  rate_card_version: 'test-2026-10',
  unpriced: [],
  complete: true,
};

describe('presentCost', () => {
  describe('a complete total', () => {
    it('is shown', () => {
      expect(presentCost(PRICED).total).toBeTruthy();
    });

    it('is rounded to money, not left at full precision', () => {
      // 1.334611875 is a true amount and an unreadable one.
      expect(presentCost(PRICED).total).toBe('1.33');
    });

    it('carries the currency', () => {
      expect(presentCost(PRICED).currency).toBe('USD');
    });

    it('names the prices that produced it', () => {
      expect(presentCost(PRICED).rateCard).toBe('test-2026-10');
    });

    it('is not called approximate', () => {
      expect(presentCost(PRICED).atLeast).toBe(false);
    });
  });

  describe('a total missing some rows', () => {
    const partial = { ...PRICED, complete: false, unpriced: ['unrecorded'] };

    it('is marked as a floor rather than the figure', () => {
      // Shown plainly as the total, somebody budgets against it.
      expect(presentCost(partial).atLeast).toBe(true);
    });

    it('names what is missing from it', () => {
      expect(presentCost(partial).unpriced).toEqual(['unrecorded']);
    });

    it('still shows the part that is known', () => {
      expect(presentCost(partial).total).toBe('1.33');
    });
  });

  describe('no prices at all', () => {
    const unpriced = {
      ...PRICED,
      total_cost: null,
      complete: false,
      rate_card_version: 'none',
    };

    it('shows no total rather than zero', () => {
      expect(presentCost(unpriced).total).toBeNull();
    });

    it('says why there is none', () => {
      expect(presentCost(unpriced).noRateCard).toBe(true);
    });
  });

  describe('one row', () => {
    it('shows a cost it has', () => {
      expect(presentCost(PRICED).cell('0.5')).toBe('0.50');
    });

    it('shows a dash for one it does not', () => {
      // Not 0.00, which reads as "this model was free".
      expect(presentCost(PRICED).cell(null)).toBe('—');
    });

    it('does not round a real amount away to nothing', () => {
      // Below a cent is still spend; rounding it to 0.00 and
      // summing a thousand of them loses real money.
      expect(presentCost(PRICED).cell('0.000125')).toBe('<0.01');
    });

    it('shows a true zero as zero', () => {
      expect(presentCost(PRICED).cell('0')).toBe('0.00');
    });
  });
});

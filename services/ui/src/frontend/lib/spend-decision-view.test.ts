import { describe, expect, it } from 'vitest';

import { presentSpendDecision } from '@/lib/spend-decision-view';

const allowed = {
  permitted: true,
  runRemaining: '4.00',
  periodRemaining: '900.00',
  currency: 'USD',
  warn: false,
  refusal: null as string | null,
  reason: '',
};

describe('presentSpendDecision', () => {
  it('shows nothing while there is plenty of money', () => {
    expect(presentSpendDecision(allowed)).toBeNull();
  });

  it('warns when a run is near its own limit', () => {
    const nearly = { ...allowed, warn: true, runRemaining: '0.40' };
    expect(presentSpendDecision(nearly)?.headline).toBe('$0.40 left for this run');
  });

  it('does not block while only warning', () => {
    const nearly = { ...allowed, warn: true, runRemaining: '0.40' };
    expect(presentSpendDecision(nearly)?.blocked).toBe(false);
  });

  it('says plainly when a run hit its own limit', () => {
    const stopped = {
      ...allowed,
      permitted: false,
      warn: true,
      runRemaining: '0.00',
      refusal: 'run-limit',
      reason: 'this run has reached its own spending limit',
    };
    expect(presentSpendDecision(stopped)?.headline).toBe('This run has spent its limit');
  });

  it('says plainly when the period budget is gone', () => {
    const stopped = {
      ...allowed,
      permitted: false,
      refusal: 'period-limit',
      reason: 'the budget for this period is spent',
    };
    expect(presentSpendDecision(stopped)?.headline).toBe('The budget for this period is spent');
  });

  it('says plainly when a run is taking more than its share', () => {
    const stopped = { ...allowed, permitted: false, refusal: 'fair-share', reason: 'x' };
    expect(presentSpendDecision(stopped)?.headline).toBe(
      'This is using more than its share of the budget',
    );
  });

  it('offers to raise a run limit', () => {
    const stopped = { ...allowed, permitted: false, refusal: 'run-limit', reason: 'x' };
    expect(presentSpendDecision(stopped)?.action).toBe('raise-run-limit');
  });

  it('offers to ask an administrator when the period budget is gone', () => {
    const stopped = { ...allowed, permitted: false, refusal: 'period-limit', reason: 'x' };
    expect(presentSpendDecision(stopped)?.action).toBe('contact-admin');
  });

  it('offers to wait when it is only a fairness problem', () => {
    const stopped = { ...allowed, permitted: false, refusal: 'fair-share', reason: 'x' };
    expect(presentSpendDecision(stopped)?.action).toBe('wait');
  });

  it('shows what is left in the period', () => {
    const stopped = { ...allowed, permitted: false, refusal: 'run-limit', reason: 'x' };
    expect(presentSpendDecision(stopped)?.detail).toBe('$900.00 left in this period');
  });

  it('treats a block as serious', () => {
    const stopped = { ...allowed, permitted: false, refusal: 'run-limit', reason: 'x' };
    expect(presentSpendDecision(stopped)?.severity).toBe('high');
  });

  it('treats a warning as a nudge', () => {
    expect(presentSpendDecision({ ...allowed, warn: true })?.severity).toBe('medium');
  });

  it('formats another currency', () => {
    const nearly = { ...allowed, warn: true, runRemaining: '0.40', currency: 'EUR' };
    expect(presentSpendDecision(nearly)?.headline).toBe('€0.40 left for this run');
  });
});

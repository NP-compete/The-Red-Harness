import { describe, expect, it } from 'vitest';

import { presentErrorBudget } from '@/lib/error-budget-view';

const budget = {
  state: 'healthy' as const,
  used: 0.5,
  failuresLeft: 50,
  mayDeploy: true,
  warn: false,
  exceptional: false,
  reason: '',
};

describe('presentErrorBudget', () => {
  it('says how much budget is left, not how much is used', () => {
    expect(presentErrorBudget(budget).headline).toBe('50% of the error budget left');
  });

  it('says how many more failures are tolerable', () => {
    expect(presentErrorBudget(budget).detail).toBe('50 more failures before changes pause');
  });

  it('shows the share used as a fraction for a bar', () => {
    expect(presentErrorBudget(budget).fraction).toBe(0.5);
  });

  it('is quiet while the service is healthy', () => {
    expect(presentErrorBudget(budget).severity).toBe('none');
  });

  it('warns when the budget is nearly gone', () => {
    const risky = { ...budget, state: 'at-risk' as const, used: 0.85, failuresLeft: 15, warn: true };
    expect(presentErrorBudget(risky).severity).toBe('medium');
  });

  it('says plainly when the budget is spent', () => {
    const spent = {
      ...budget,
      state: 'exhausted' as const,
      used: 1,
      failuresLeft: 0,
      mayDeploy: false,
      reason: 'the error budget is spent',
    };
    expect(presentErrorBudget(spent).headline).toBe('The error budget is spent');
  });

  it('treats a spent budget as serious', () => {
    const spent = { ...budget, state: 'exhausted' as const, used: 1, mayDeploy: false, reason: 'x' };
    expect(presentErrorBudget(spent).severity).toBe('high');
  });

  it('says changes are paused rather than forbidden', () => {
    const spent = { ...budget, state: 'exhausted' as const, used: 1, mayDeploy: false, reason: 'x' };
    expect(presentErrorBudget(spent).detail).toBe('Changes are paused until reliability recovers');
  });

  it('still offers a way to ship an urgent fix', () => {
    const spent = { ...budget, state: 'exhausted' as const, used: 1, mayDeploy: false, reason: 'x' };
    expect(presentErrorBudget(spent).action).toBe('ship-fix');
  });

  it('marks an exceptional release so it is visible afterwards', () => {
    const override = {
      ...budget,
      state: 'exhausted' as const,
      used: 1,
      mayDeploy: true,
      exceptional: true,
      reason: 'x',
    };
    expect(presentErrorBudget(override).note).toBe('Released while the budget was spent');
  });

  it('has no such note for an ordinary release', () => {
    expect(presentErrorBudget(budget).note).toBe('');
  });

  it('offers nothing to act on while healthy', () => {
    expect(presentErrorBudget(budget).action).toBe('none');
  });

  it('says plainly when there is not enough history to judge', () => {
    const unknown = { ...budget, state: 'unknown' as const, used: 0, failuresLeft: 0, reason: 'x' };
    expect(presentErrorBudget(unknown).headline).toBe('Not enough history yet');
  });

  it('does not draw a bar without data', () => {
    const unknown = { ...budget, state: 'unknown' as const, used: 0, failuresLeft: 0, reason: 'x' };
    expect(presentErrorBudget(unknown).fraction).toBeNull();
  });
});

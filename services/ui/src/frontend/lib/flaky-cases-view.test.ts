import { describe, expect, it } from 'vitest';

import { presentFlakiness } from '@/lib/flaky-cases-view';

const flakiness = {
  cases: {
    steady: { stability: 'steady' as const, passes: true, passRate: 1, attempts: 5, reason: '' },
    wobbly: {
      stability: 'flaky' as const,
      passes: false,
      passRate: 0.5,
      attempts: 4,
      reason: 'passed 2 of 4 times',
    },
    untried: {
      stability: 'unknown' as const,
      passes: true,
      passRate: 1,
      attempts: 1,
      reason: '3 attempts are needed before judging this',
    },
  },
  flaky: ['wobbly'],
  flakyShare: 1 / 3,
  worst: 'wobbly',
  mayGate: false,
};

describe('presentFlakiness', () => {
  it('shows only the cases worth acting on', () => {
    expect(presentFlakiness(flakiness).rows.map((row) => row.caseId)).toEqual([
      'wobbly',
      'untried',
    ]);
  });

  it('puts flaky cases before untried ones', () => {
    expect(presentFlakiness(flakiness).rows[0].caseId).toBe('wobbly');
  });

  it('describes a flaky case in plain words', () => {
    expect(presentFlakiness(flakiness).rows[0].description).toBe('passed 2 of 4 times');
  });

  it('describes an untried case plainly', () => {
    expect(presentFlakiness(flakiness).rows[1].description).toBe(
      '3 attempts are needed before judging this',
    );
  });

  it('marks the worst offender', () => {
    expect(presentFlakiness(flakiness).rows[0].worst).toBe(true);
  });

  it('does not mark the others as worst', () => {
    expect(presentFlakiness(flakiness).rows[1].worst).toBe(false);
  });

  it('says plainly that the suite cannot gate releases', () => {
    expect(presentFlakiness(flakiness).headline).toBe('This suite cannot decide releases yet');
  });

  it('says plainly when the suite is trustworthy', () => {
    const solid = { ...flakiness, flaky: [], flakyShare: 0, worst: '', mayGate: true };
    expect(presentFlakiness(solid).headline).toBe('This suite is steady');
  });

  it('says how much of the suite wobbles', () => {
    expect(presentFlakiness(flakiness).detail).toBe('33% of cases are unreliable');
  });

  it('has no such detail when nothing wobbles', () => {
    const solid = { ...flakiness, flaky: [], flakyShare: 0, worst: '', mayGate: true };
    expect(presentFlakiness(solid).detail).toBe('');
  });

  it('suggests running the untried cases more', () => {
    expect(presentFlakiness(flakiness).action).toBe('run-again');
  });

  it('suggests nothing when the suite is steady', () => {
    const solid = { ...flakiness, flaky: [], flakyShare: 0, worst: '', mayGate: true };
    expect(presentFlakiness(solid).action).toBe('none');
  });

  it('treats an unreliable suite as worth acting on', () => {
    expect(presentFlakiness(flakiness).severity).toBe('medium');
  });

  it('shows no rows for a steady suite', () => {
    const solid = {
      cases: { steady: flakiness.cases.steady },
      flaky: [],
      flakyShare: 0,
      worst: '',
      mayGate: true,
    };
    expect(presentFlakiness(solid).rows).toEqual([]);
  });
});

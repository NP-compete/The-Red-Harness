import { describe, expect, it } from 'vitest';

import { presentDeadline } from '@/lib/deadline-view';

const state = {
  remainingSeconds: 600,
  limitSeconds: 900,
  outcome: 'continue' as const,
  warn: false,
  reason: '',
};

describe('presentDeadline', () => {
  it('says how much time is left', () => {
    expect(presentDeadline(state).label).toBe('10 minutes left');
  });

  it('switches to seconds when that is all there is', () => {
    expect(presentDeadline({ ...state, remainingSeconds: 45, warn: true }).label).toBe(
      '45 seconds left',
    );
  });

  it('shows how far through the run is', () => {
    expect(presentDeadline(state).fraction).toBeCloseTo(0.333, 2);
  });

  it('shows a finished run as fully used', () => {
    const done = { ...state, remainingSeconds: 0, outcome: 'out-of-time' as const, warn: true };
    expect(presentDeadline(done).fraction).toBe(1);
  });

  it('never reports more than fully used', () => {
    const over = { ...state, remainingSeconds: -120, outcome: 'out-of-time' as const, warn: true };
    expect(presentDeadline(over).fraction).toBe(1);
  });

  it('says plainly when the time ran out', () => {
    const done = { ...state, remainingSeconds: 0, outcome: 'out-of-time' as const, warn: true };
    expect(presentDeadline(done).label).toBe('Out of time');
  });

  it('says the run stopped rather than failed', () => {
    const done = { ...state, remainingSeconds: 0, outcome: 'out-of-time' as const, warn: true };
    expect(presentDeadline(done).failed).toBe(false);
  });

  it('explains when a step was too long to start', () => {
    const skipped = {
      ...state,
      remainingSeconds: 20,
      outcome: 'step-too-long' as const,
      warn: true,
      reason: 'the next step needs about 30s and only 20s remain',
    };
    expect(presentDeadline(skipped).detail).toBe(
      'the next step needs about 30s and only 20s remain',
    );
  });

  it('marks a warning so it can be shown differently', () => {
    expect(presentDeadline({ ...state, remainingSeconds: 60, warn: true }).urgent).toBe(true);
  });

  it('does not mark a comfortable run', () => {
    expect(presentDeadline(state).urgent).toBe(false);
  });

  it('offers more time while the run is still going', () => {
    expect(presentDeadline(state).action).toBe('extend');
  });

  it('offers to start again once the time is gone', () => {
    const done = { ...state, remainingSeconds: 0, outcome: 'out-of-time' as const, warn: true };
    expect(presentDeadline(done).action).toBe('restart');
  });

  it('shows no clock at all for a run without a limit', () => {
    const endless = { ...state, remainingSeconds: null, limitSeconds: null };
    expect(presentDeadline(endless)).toBeNull();
  });
});

import { describe, expect, it } from 'vitest';

import { presentRollout } from '@/lib/rollout-view';

const rollout = {
  version: '4.2',
  previousVersion: '4.1',
  share: 0.25,
  steps: [0.05, 0.25, 1],
  state: 'advanced' as const,
  reason: '',
  runs: 200,
};

describe('presentRollout', () => {
  it('says what share of runs sees the new version', () => {
    expect(presentRollout(rollout).headline).toBe('4.2 is serving 25% of runs');
  });

  it('says which version everyone else sees', () => {
    expect(presentRollout(rollout).fallback).toBe('Everyone else is on 4.1');
  });

  it('shows how far through the steps it is', () => {
    expect(presentRollout(rollout).progress).toBe('step 2 of 3');
  });

  it('says a version not yet serving anyone has not started', () => {
    const shown = presentRollout({ ...rollout, share: 0, state: 'waiting' });
    expect(shown.headline).toBe('4.2 is not serving any runs yet');
  });

  it('reads a completed rollout as finished rather than as a step', () => {
    const shown = presentRollout({ ...rollout, share: 1, state: 'complete' });
    expect(shown.progress).toBe('finished');
  });

  it('drops the fallback once nobody is on the old version', () => {
    const shown = presentRollout({ ...rollout, share: 1, state: 'complete' });
    expect(shown.fallback).toBe('');
  });

  it('shows a rollback as a rollback, not as progress', () => {
    const shown = presentRollout({
      ...rollout,
      share: 0,
      state: 'rolled-back',
      reason: 'failures rose from 1% to 8%; serving 4.1 again',
    });
    expect(shown.headline).toBe('4.2 was rolled back');
  });

  it('carries the reason for a rollback through unchanged', () => {
    const shown = presentRollout({
      ...rollout,
      state: 'rolled-back',
      reason: 'failures rose from 1% to 8%; serving 4.1 again',
    });
    expect(shown.detail).toBe('failures rose from 1% to 8%; serving 4.1 again');
  });

  it('treats a rollback as needing attention', () => {
    expect(presentRollout({ ...rollout, state: 'rolled-back' }).needsAttention).toBe(true);
  });

  it('does not treat normal progress as needing attention', () => {
    expect(presentRollout(rollout).needsAttention).toBe(false);
  });

  it('says a held rollout is held on purpose', () => {
    expect(presentRollout({ ...rollout, state: 'halted' }).detail).toContain('held');
  });

  it('does not treat a deliberate hold as a fault', () => {
    expect(presentRollout({ ...rollout, state: 'halted' }).needsAttention).toBe(false);
  });

  it('offers to hold a rollout that is moving', () => {
    expect(presentRollout(rollout).action).toBe('hold');
  });

  it('offers to resume a rollout that is held', () => {
    expect(presentRollout({ ...rollout, state: 'halted' }).action).toBe('resume');
  });

  it('offers nothing to act on once it is finished', () => {
    expect(presentRollout({ ...rollout, share: 1, state: 'complete' }).action).toBe('none');
  });

  it('says how much evidence the decision rests on', () => {
    expect(presentRollout(rollout).evidence).toBe('200 runs so far');
  });
});

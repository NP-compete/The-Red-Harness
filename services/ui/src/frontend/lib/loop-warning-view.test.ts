import { describe, expect, it } from 'vitest';

import { presentLoop } from '@/lib/loop-warning-view';

const fine = {
  pattern: 'progressing' as const,
  shouldStop: false,
  repeated: '',
  times: 0,
  reason: '',
};

describe('presentLoop', () => {
  it('shows nothing while the run is getting somewhere', () => {
    expect(presentLoop(fine)).toBeNull();
  });

  it('says plainly when the same call keeps repeating', () => {
    const stuck = {
      ...fine,
      pattern: 'repeating' as const,
      shouldStop: true,
      repeated: 'search',
      times: 3,
      reason: 'search has been called 3 times with the same arguments',
    };
    expect(presentLoop(stuck)?.headline).toBe('This run is repeating itself');
  });

  it('gives the detail it was told', () => {
    const stuck = {
      ...fine,
      pattern: 'repeating' as const,
      shouldStop: true,
      repeated: 'search',
      times: 3,
      reason: 'search has been called 3 times with the same arguments',
    };
    expect(presentLoop(stuck)?.detail).toBe('search has been called 3 times with the same arguments');
  });

  it('describes two calls bouncing off each other', () => {
    const bouncing = {
      ...fine,
      pattern: 'alternating' as const,
      shouldStop: true,
      repeated: 'a/b',
      reason: 'x',
    };
    expect(presentLoop(bouncing)?.headline).toBe('This run is going back and forth');
  });

  it('describes a run hitting the same error', () => {
    const failing = {
      ...fine,
      pattern: 'same-failure' as const,
      shouldStop: true,
      repeated: 'fetch',
      reason: 'the last 4 calls all returned: connection refused',
    };
    expect(presentLoop(failing)?.headline).toBe('This run keeps hitting the same problem');
  });

  it('says the run was stopped rather than that it failed', () => {
    const stuck = { ...fine, pattern: 'repeating' as const, shouldStop: true, reason: 'x' };
    expect(presentLoop(stuck)?.failed).toBe(false);
  });

  it('offers to point the run somewhere else', () => {
    const stuck = { ...fine, pattern: 'repeating' as const, shouldStop: true, reason: 'x' };
    expect(presentLoop(stuck)?.action).toBe('redirect');
  });

  it('treats a stopped loop as worth attention', () => {
    const stuck = { ...fine, pattern: 'repeating' as const, shouldStop: true, reason: 'x' };
    expect(presentLoop(stuck)?.severity).toBe('medium');
  });

  it('names what was repeating so it can be seen', () => {
    const stuck = { ...fine, pattern: 'repeating' as const, shouldStop: true, repeated: 'search', reason: 'x' };
    expect(presentLoop(stuck)?.culprit).toBe('search');
  });

  it('shows a loop noticed but not stopped as advice', () => {
    const noticed = { ...fine, pattern: 'alternating' as const, shouldStop: false, reason: 'x' };
    expect(presentLoop(noticed)?.severity).toBe('info');
  });

  it('does not offer to redirect a run that is still going', () => {
    const noticed = { ...fine, pattern: 'alternating' as const, shouldStop: false, reason: 'x' };
    expect(presentLoop(noticed)?.action).toBe('none');
  });

  it('never claims the loop produced an answer', () => {
    const stuck = { ...fine, pattern: 'repeating' as const, shouldStop: true, reason: 'x' };
    expect(presentLoop(stuck)?.answered).toBe(false);
  });
});

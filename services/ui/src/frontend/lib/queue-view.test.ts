import { describe, expect, it } from 'vitest';

import { presentQueue } from '@/lib/queue-view';

const waiting = {
  startsNow: false,
  position: 3,
  estimatedWaitSeconds: 360,
  refused: false,
  reason: '',
};

describe('presentQueue', () => {
  it('shows nothing when the run starts straight away', () => {
    expect(presentQueue({ ...waiting, startsNow: true, position: 0 })).toBeNull();
  });

  it('says where in the queue the run is', () => {
    expect(presentQueue(waiting)?.headline).toBe('3rd in the queue');
  });

  it('says plainly when the run is next', () => {
    expect(presentQueue({ ...waiting, position: 1 })?.headline).toBe('Next in the queue');
  });

  it('uses the right ordinal for second place', () => {
    expect(presentQueue({ ...waiting, position: 2 })?.headline).toBe('2nd in the queue');
  });

  it('gives an estimate in plain words', () => {
    expect(presentQueue(waiting)?.estimate).toBe('about 6 minutes');
  });

  it('gives an estimate in seconds when it is short', () => {
    expect(presentQueue({ ...waiting, estimatedWaitSeconds: 40 })?.estimate).toBe('under a minute');
  });

  it('says nothing rather than guessing when there is no estimate', () => {
    expect(presentQueue({ ...waiting, estimatedWaitSeconds: null })?.estimate).toBe('');
  });

  it('marks the estimate as an estimate', () => {
    expect(presentQueue(waiting)?.estimateIsApproximate).toBe(true);
  });

  it('lets the person give up waiting', () => {
    expect(presentQueue(waiting)?.action).toBe('cancel');
  });

  it('says plainly when the queue would not take the run', () => {
    const refused = {
      ...waiting,
      refused: true,
      position: 0,
      reason: 'ana already has 5 runs waiting',
    };
    expect(presentQueue(refused)?.headline).toBe('Not queued');
  });

  it('shows why a run was not queued', () => {
    const refused = { ...waiting, refused: true, position: 0, reason: 'too many waiting' };
    expect(presentQueue(refused)?.detail).toBe('too many waiting');
  });

  it('offers to try later rather than to cancel a run that never queued', () => {
    const refused = { ...waiting, refused: true, position: 0, reason: 'x' };
    expect(presentQueue(refused)?.action).toBe('retry-later');
  });

  it('treats a refusal as more serious than waiting', () => {
    const refused = { ...waiting, refused: true, position: 0, reason: 'x' };
    expect(presentQueue(refused)?.severity).toBe('medium');
    expect(presentQueue(waiting)?.severity).toBe('low');
  });

  it('never claims the run has started while it waits', () => {
    expect(presentQueue(waiting)?.started).toBe(false);
  });
});

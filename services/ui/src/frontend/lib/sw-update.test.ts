import { describe, expect, it } from 'vitest';

import { updateDecision } from '@/lib/sw-update';

/**
 * What to do when a new version is waiting.
 *
 * Swapping the application out from under somebody mid-answer loses
 * what is on their screen. Leaving them on a stale one indefinitely
 * is the other failure, and quieter. So: never while they are busy,
 * and never silently.
 */
describe('updateDecision', () => {
  const waiting = { waiting: true, busy: false, dismissed: false };

  it('does nothing when there is no new version', () => {
    expect(updateDecision({ ...waiting, waiting: false }).action).toBe('none');
  });

  it('offers the update when one is waiting', () => {
    expect(updateDecision(waiting).action).toBe('offer');
  });

  it('never swaps without being asked', () => {
    // Reloading on its own is how somebody loses a half-written
    // message to a version bump.
    expect(updateDecision(waiting).action).not.toBe('apply');
  });

  it('waits while a run is in flight', () => {
    expect(updateDecision({ ...waiting, busy: true }).action).toBe('none');
  });

  it('offers again once the run has finished', () => {
    expect(updateDecision({ ...waiting, busy: false }).action).toBe('offer');
  });

  it('stops offering once somebody has said not now', () => {
    expect(updateDecision({ ...waiting, dismissed: true }).action).toBe('none');
  });

  it('says a reload is what applying it means', () => {
    // So the offer is not a button whose consequence is a surprise.
    expect(updateDecision(waiting).reloads).toBe(true);
  });
});

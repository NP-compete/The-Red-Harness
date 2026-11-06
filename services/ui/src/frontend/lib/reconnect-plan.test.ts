import { describe, expect, it } from 'vitest';

import {
  afterIncompleteStream,
  keepTrying,
  reconnectPlan,
  shouldSchedule,
} from './reconnect-plan';

describe('reconnectPlan', () => {
  const plan = reconnectPlan(3, 15000);

  it('tries as many times as it is allowed', () => {
    expect(plan.filter((step) => !step.giveUp).map((step) => step.attempt)).toEqual([
      1, 2, 3,
    ]);
  });

  it('starts trying at once', () => {
    expect(plan[0].atMs).toBe(0);
  });

  it('spaces the attempts out', () => {
    expect(plan.slice(0, 3).map((step) => step.atMs)).toEqual([0, 15000, 30000]);
  });

  it('gives up after the last attempt rather than waiting for ever', () => {
    // Without this the conversation sits on "Attempt 3 of 3" with
    // the composer disabled, and nothing ever says it is over.
    expect(plan.at(-1)).toEqual({ atMs: 45000, attempt: 3, giveUp: true });
  });

  it('gives up after the last attempt has had its own interval', () => {
    const last = plan.at(-2);
    expect(plan.at(-1)!.atMs - last!.atMs).toBe(15000);
  });

  it('gives up immediately when no attempts are allowed', () => {
    expect(reconnectPlan(0, 15000)).toEqual([{ atMs: 0, attempt: 0, giveUp: true }]);
  });

  it('copes with a single attempt', () => {
    expect(reconnectPlan(1, 5000)).toEqual([
      { atMs: 0, attempt: 1, giveUp: false },
      { atMs: 5000, attempt: 1, giveUp: true },
    ]);
  });
});

describe('a plan that is already running', () => {
  it('is not started again while it is still going', () => {
    // Every failed attempt comes back through the same error path.
    // Rescheduling there restarts the countdown, so the run sits on
    // "Attempt 1 of 3" and the step that gives up never arrives.
    expect(shouldSchedule({ alreadyScheduled: true })).toBe(false);
  });

  it('is started when nothing is pending', () => {
    expect(shouldSchedule({ alreadyScheduled: false })).toBe(true);
  });
});

describe('what to show when a stream ends without finishing', () => {
  it('arms a reconnection the first time', () => {
    const state = afterIncompleteStream({ gaveUp: false, reason: 'socket closed', dropped: true });
    expect(state.isLoading).toBe(true);
    expect(state.isReconnecting).toBe(true);
    expect(state.reconnectAttempt).toBe(1);
  });

  it('does not arm another once the attempts are spent', () => {
    // Otherwise the give-up hands the composer back and the next
    // closed stream immediately takes it away again.
    const state = afterIncompleteStream({ gaveUp: true, reason: 'socket closed', dropped: true });
    expect(state.isLoading).toBe(false);
    expect(state.isReconnecting).toBe(false);
  });

  it('says why, once it has stopped trying', () => {
    expect(afterIncompleteStream({ gaveUp: true, reason: 'socket closed', dropped: true }).error)
      .toBe('socket closed');
  });

  it('says nothing is wrong while it is still trying', () => {
    expect(afterIncompleteStream({ gaveUp: false, reason: 'socket closed', dropped: true }).error)
      .toBeNull();
  });

  it('has something to say when the reason is unknown', () => {
    expect(afterIncompleteStream({ gaveUp: true, reason: '', dropped: false }).error).toBeTruthy();
  });

  it('remembers whether the reply was cut off mid-flow', () => {
    expect(afterIncompleteStream({ gaveUp: false, reason: '', dropped: true }).streamDroppedMidResponse).toBe(true);
  });

  it('still remembers it was cut off once it has given up', () => {
    // The footer under the reply reads this. Forgetting it there
    // leaves a truncated answer wearing a completion time.
    expect(
      afterIncompleteStream({ gaveUp: true, reason: 'boom', dropped: true })
        .streamDroppedMidResponse,
    ).toBe(true);
  });
});

describe('whether to start another attempt', () => {
  it('carries on while there is still hope', () => {
    expect(keepTrying({ gaveUp: false, cancelled: false })).toBe(true);
  });

  it('stops once the plan has given up', () => {
    // The attempt loop re-arms the reconnection banner at the top of
    // every attempt. Left running after the give-up, it takes the
    // composer back a few seconds after handing it over.
    expect(keepTrying({ gaveUp: true, cancelled: false })).toBe(false);
  });

  it('stops when the person stopped it', () => {
    expect(keepTrying({ gaveUp: false, cancelled: true })).toBe(false);
  });
});

import { describe, expect, it } from 'vitest';

import { presentRefusal } from '@/lib/refusal';

describe('presentRefusal', () => {
  it('offers to connect the system the run could not reach', () => {
    const shown = presentRefusal({
      code: 'no_authority',
      message: 'You have not connected tracker.',
      remedy: 'Connect tracker and run this again.',
      server: 'tracker',
    });

    expect(shown.detail).toBe('You have not connected tracker.');
    expect(shown.action).toEqual({ kind: 'connect', label: 'Connect tracker', target: 'tracker' });
  });

  it('offers no connect action when no server is named', () => {
    const shown = presentRefusal({
      code: 'no_authority',
      message: 'Not connected.',
      remedy: 'Connect and try again.',
    });

    expect(shown.action).toBeUndefined();
  });

  it('points a budget refusal at starting a new conversation', () => {
    const shown = presentRefusal({
      code: 'budget_exhausted',
      message: 'This run has used its budget.',
      remedy: 'Start a new run, or ask an administrator to raise the budget.',
    });

    expect(shown.action).toEqual({ kind: 'new-conversation', label: 'Start a new conversation' });
  });

  it('gives a policy refusal no action, because the user cannot resolve it', () => {
    const shown = presentRefusal({
      code: 'policy_denied',
      message: 'Policy denies tracker.create_issue.',
      remedy: 'Ask an administrator to change the approval policy for this tool.',
    });

    expect(shown.action).toBeUndefined();
    expect(shown.detail).toContain('Policy denies');
  });

  it('always surfaces the remedy, because a refusal without one is a dead end', () => {
    const shown = presentRefusal({
      code: 'policy_denied',
      message: 'No.',
      remedy: 'Ask an administrator.',
    });

    expect(shown.remedy).toBe('Ask an administrator.');
  });

  it('falls back to a readable title for an unknown code', () => {
    const shown = presentRefusal({
      code: 'something_new' as never,
      message: 'Refused.',
      remedy: 'Try later.',
    });

    expect(shown.title).toBeTruthy();
    expect(shown.action).toBeUndefined();
  });

  it('never renders an empty detail', () => {
    const shown = presentRefusal({ code: 'policy_denied', message: '', remedy: 'Ask.' });
    expect(shown.detail.length).toBeGreaterThan(0);
  });
});

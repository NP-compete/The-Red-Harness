import { beforeEach, describe, expect, it } from 'vitest';

import {
  chosenFor,
  chooseFor,
  forgetThread,
  offerIsWorthMaking,
  type ReasoningProfile,
} from './reasoning-choice';

/**
 * Which way of answering this conversation is using.
 *
 * Per thread, not per person: one conversation may be a quick
 * lookup and the next a long investigation, and carrying a
 * choice from the first into the second is how somebody ends up
 * paying for careful work on "what time is it".
 *
 * The agent decides whether the choice is worth offering — it is
 * the only thing that knows whether two profiles would send
 * different requests. What is decided here is what to do with
 * the answer, including the two awkward cases: a thread holding
 * a choice the deployment has since withdrawn, and a thread that
 * has never chosen.
 */

const OFFERED: ReasoningProfile[] = [
  { name: 'fast', effort: 'low' },
  { name: 'balanced', effort: 'medium' },
  { name: 'accurate', effort: 'high' },
];

describe('whether to show the control at all', () => {
  it('not when the agent offers nothing', () => {
    // Which is what it says when the profiles would all send the
    // same request. An empty menu would be worse than no menu.
    expect(offerIsWorthMaking([])).toBe(false);
  });

  it('not when there is only one way to answer', () => {
    expect(offerIsWorthMaking([{ name: 'only', effort: 'low' }])).toBe(false);
  });

  it('yes when there is a real choice', () => {
    expect(offerIsWorthMaking(OFFERED)).toBe(true);
  });

  it('not when the answer is not a list', () => {
    expect(offerIsWorthMaking(undefined as unknown as ReasoningProfile[])).toBe(false);
  });
});

describe('remembering the choice', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('nothing is chosen to begin with', () => {
    expect(chosenFor('thread-1', OFFERED)).toBeNull();
  });

  it('keeps what was chosen', () => {
    chooseFor('thread-1', 'accurate');
    expect(chosenFor('thread-1', OFFERED)).toBe('accurate');
  });

  it('keeps it per thread', () => {
    // The whole point. A long investigation and a quick lookup
    // are different conversations and want different answers.
    chooseFor('thread-1', 'accurate');
    chooseFor('thread-2', 'fast');
    expect(chosenFor('thread-1', OFFERED)).toBe('accurate');
    expect(chosenFor('thread-2', OFFERED)).toBe('fast');
  });

  it('a thread that never chose is unaffected by one that did', () => {
    chooseFor('thread-1', 'accurate');
    expect(chosenFor('thread-2', OFFERED)).toBeNull();
  });

  it('forgets a thread when it is deleted', () => {
    chooseFor('thread-1', 'accurate');
    forgetThread('thread-1');
    expect(chosenFor('thread-1', OFFERED)).toBeNull();
  });
});

describe('a choice the deployment has withdrawn', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('is not used', () => {
    // A thread chose "accurate" and the deployment has since
    // removed it. Sending a name the agent no longer knows is
    // how a conversation silently stops being routed anywhere.
    chooseFor('thread-1', 'accurate');
    expect(chosenFor('thread-1', [{ name: 'fast', effort: 'low' }])).toBeNull();
  });

  it('is not used when nothing is offered at all', () => {
    // The deployment turned the whole thing off. Every thread
    // goes back to the agent's own default.
    chooseFor('thread-1', 'accurate');
    expect(chosenFor('thread-1', [])).toBeNull();
  });

  it('comes back if the deployment restores it', () => {
    // Not deleted on read: a deployment reverting a change
    // should not have cost everybody their choice.
    chooseFor('thread-1', 'accurate');
    expect(chosenFor('thread-1', [{ name: 'fast', effort: 'low' }])).toBeNull();
    expect(chosenFor('thread-1', OFFERED)).toBe('accurate');
  });
});

describe('it never breaks the composer', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('survives unreadable storage', () => {
    localStorage.setItem('template-ui-reasoning', 'not json');
    expect(chosenFor('thread-1', OFFERED)).toBeNull();
  });

  it('survives storage holding the wrong shape', () => {
    localStorage.setItem('template-ui-reasoning', '["an array"]');
    expect(chosenFor('thread-1', OFFERED)).toBeNull();
  });

  it('ignores a thread with no name', () => {
    chooseFor('', 'accurate');
    expect(chosenFor('', OFFERED)).toBeNull();
  });
});

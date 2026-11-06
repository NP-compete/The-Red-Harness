import { describe, expect, it } from 'vitest';

import { presentFeedbackOutcome } from '@/lib/feedback-outcome-view';

const thanked = {
  run: 'r1',
  action: 'thank' as const,
  comment: '',
  askedForDetail: false,
  attachContent: true,
  becomesEvalCase: false,
};

describe('presentFeedbackOutcome', () => {
  it('thanks someone briefly', () => {
    expect(presentFeedbackOutcome(thanked).message).toBe('Thanks');
  });

  it('asks nothing further of someone who liked the answer', () => {
    expect(presentFeedbackOutcome(thanked).prompt).toBe('');
  });

  it('asks what went wrong when it needs to know', () => {
    const asking = { ...thanked, action: 'ask_why' as const, askedForDetail: true };
    expect(presentFeedbackOutcome(asking).prompt).toBe('What went wrong?');
  });

  it('offers reasons rather than only a blank box', () => {
    const asking = { ...thanked, action: 'ask_why' as const, askedForDetail: true };
    expect(presentFeedbackOutcome(asking).choices).toEqual([
      'Wrong answer',
      'Missed something',
      'Too slow',
      'Something else',
    ]);
  });

  it('offers no choices once it has been told', () => {
    const filed = { ...thanked, action: 'file' as const, comment: 'the number was wrong' };
    expect(presentFeedbackOutcome(filed).choices).toEqual([]);
  });

  it('confirms that a complaint was recorded', () => {
    const filed = { ...thanked, action: 'file' as const, comment: 'the number was wrong' };
    expect(presentFeedbackOutcome(filed).message).toBe('Recorded — thanks for the detail');
  });

  it('says plainly where a complaint about a refusal goes', () => {
    const routed = { ...thanked, action: 'route_to_policy' as const, comment: 'should be allowed' };
    expect(presentFeedbackOutcome(routed).message).toBe(
      'Passed to whoever sets the rules for this workspace',
    );
  });

  it('says when the conversation goes with the report', () => {
    const filed = { ...thanked, action: 'file' as const, comment: 'wrong' };
    expect(presentFeedbackOutcome(filed).detail).toBe('This conversation is attached');
  });

  it('says when the conversation stays behind', () => {
    const filed = { ...thanked, action: 'file' as const, comment: 'wrong', attachContent: false };
    expect(presentFeedbackOutcome(filed).detail).toBe(
      'Only the rating is sent, not the conversation',
    );
  });

  it('adds no detail when nothing was sent anywhere', () => {
    expect(presentFeedbackOutcome(thanked).detail).toBe('');
  });

  it('waits for an answer only while it is asking', () => {
    const asking = { ...thanked, action: 'ask_why' as const, askedForDetail: true };
    expect(presentFeedbackOutcome(asking).awaitingReply).toBe(true);
  });

  it('does not wait once it has what it needs', () => {
    const filed = { ...thanked, action: 'file' as const, comment: 'wrong' };
    expect(presentFeedbackOutcome(filed).awaitingReply).toBe(false);
  });
});

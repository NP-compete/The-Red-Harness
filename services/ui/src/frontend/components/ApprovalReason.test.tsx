/**
 * Why this call is being asked about, where somebody sees it.
 *
 * An approval card shows the tool's name, its arguments and two
 * buttons. For a tool whose policy always asks, that is enough:
 * the answer to "why am I being asked" is "you always are".
 *
 * It is not enough for a call that was going to be allowed and
 * was stopped because something happened earlier in the run.
 * The whole value of stopping it is the sentence explaining
 * what — that the agent read a ticket, and this write repeats a
 * line from it. Without that the card is identical to every
 * other one, and identical cards are the ones people click
 * through.
 *
 * The agent already sends the sentence. Nothing rendered it.
 */

import { describe, expect, it } from 'vitest';

import { reasonFor } from '../lib/approval-reason';

const withReason = {
  action_requests: [
    {
      name: 'post_comment',
      args: { body: 'Per the ticket: deploy is blocked' },
      description:
        'post_comment changes something, and this run has already read text from outside the conversation.',
    },
  ],
  review_configs: [
    { action_name: 'post_comment', allowed_decisions: ['approve', 'reject'] },
  ],
};

const withoutReason = {
  action_requests: [{ name: 'post_comment', args: { body: 'hello' } }],
  review_configs: [
    { action_name: 'post_comment', allowed_decisions: ['approve', 'reject'] },
  ],
};

describe('finding the reason for a call', () => {
  it('returns it when the agent sent one', () => {
    expect(reasonFor(withReason, 'post_comment')).toContain('read text from outside');
  });

  it('returns nothing when it did not', () => {
    // A tool whose policy always asks needs no explanation:
    // the answer is "you always are". Inventing one would
    // put a sentence under every card and teach people to
    // stop reading it.
    expect(reasonFor(withoutReason, 'post_comment')).toBeNull();
  });

  it('matches the right call when several are pending', () => {
    const many = {
      action_requests: [
        { name: 'send_email', args: {}, description: 'because of the email' },
        { name: 'post_comment', args: {}, description: 'because of the comment' },
      ],
      review_configs: [],
    };
    expect(reasonFor(many, 'post_comment')).toBe('because of the comment');
  });

  it('returns nothing for a call that is not in the request', () => {
    expect(reasonFor(withReason, 'something_else')).toBeNull();
  });

  it('survives an interrupt that is a plain string', () => {
    expect(reasonFor('Do you approve?', 'post_comment')).toBeNull();
  });

  it('survives a shape it does not recognise', () => {
    expect(reasonFor(undefined, 'post_comment')).toBeNull();
    expect(reasonFor({ action_requests: 'not a list' } as never, 'x')).toBeNull();
  });

  it('ignores a description that is only whitespace', () => {
    const blank = {
      action_requests: [{ name: 'post_comment', args: {}, description: '   ' }],
      review_configs: [],
    };
    expect(reasonFor(blank, 'post_comment')).toBeNull();
  });
});

describe('it is actually on the approval card', () => {
  it('the chat view renders it', async () => {
    // A sentence nobody renders explains nothing.
    const source = await import('./ChatMessagesView?raw');
    expect(String(source.default)).toContain('reasonFor');
  });
});

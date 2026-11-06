import { describe, expect, it } from 'vitest';

import { presentFeedback } from '@/lib/feedback-view';

const state = {
  runId: 'run-1',
  rating: null as 'up' | 'down' | null,
  comment: '',
  submitted: false,
  shareTranscript: false,
  containsSensitiveData: false,
};

describe('presentFeedback', () => {
  it('asks for a rating before anything else', () => {
    expect(presentFeedback(state).prompt).toBe('Was this useful?');
  });

  it('does not ask for a comment until a rating is given', () => {
    expect(presentFeedback(state).showComment).toBe(false);
  });

  it('asks for a comment once a rating is given', () => {
    expect(presentFeedback({ ...state, rating: 'down' }).showComment).toBe(true);
  });

  it('asks what went wrong after a negative rating', () => {
    expect(presentFeedback({ ...state, rating: 'down' }).commentPrompt).toBe(
      'What went wrong? (optional)',
    );
  });

  it('asks what worked after a positive rating', () => {
    expect(presentFeedback({ ...state, rating: 'up' }).commentPrompt).toBe(
      'What worked well? (optional)',
    );
  });

  it('cannot be sent without a rating', () => {
    expect(presentFeedback(state).canSubmit).toBe(false);
  });

  it('can be sent with only a rating', () => {
    expect(presentFeedback({ ...state, rating: 'up' }).canSubmit).toBe(true);
  });

  it('offers to attach the conversation', () => {
    expect(presentFeedback({ ...state, rating: 'down' }).shareOption).toBe(
      'Include this conversation so it can be looked at',
    );
  });

  it('does not attach the conversation unless asked', () => {
    expect(presentFeedback({ ...state, rating: 'down' }).sharing).toBe(false);
  });

  it('warns before attaching a conversation holding sensitive data', () => {
    const risky = { ...state, rating: 'down' as const, shareTranscript: true, containsSensitiveData: true };
    expect(presentFeedback(risky).warning).toBe(
      'This conversation contains sensitive data that would be shared',
    );
  });

  it('does not warn when nothing sensitive is being shared', () => {
    const fine = { ...state, rating: 'down' as const, shareTranscript: true };
    expect(presentFeedback(fine).warning).toBe('');
  });

  it('does not warn about sensitive data that stays put', () => {
    const risky = { ...state, rating: 'down' as const, containsSensitiveData: true };
    expect(presentFeedback(risky).warning).toBe('');
  });

  it('thanks the person once it is sent', () => {
    expect(presentFeedback({ ...state, rating: 'up', submitted: true }).prompt).toBe('Thanks');
  });

  it('cannot be sent twice', () => {
    expect(presentFeedback({ ...state, rating: 'up', submitted: true }).canSubmit).toBe(false);
  });

  it('does not promise a reply', () => {
    const shown = presentFeedback({ ...state, rating: 'down', submitted: true });
    expect(shown.prompt.toLowerCase()).not.toContain('reply');
  });
});

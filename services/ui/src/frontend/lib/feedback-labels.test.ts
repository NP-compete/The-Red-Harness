import { describe, expect, it } from 'vitest';

import en from '../i18n/locales/en.json';
import { feedbackLabel, forkLabel } from './feedback-labels';

/**
 * These functions return catalogue keys, not words: they run outside
 * a component where there is no translator to call. The assertions
 * are still about what a person reads, so each key is resolved
 * through English here — which also proves the key exists.
 */
function said(key: string): string {
  const [section, name] = key.split('.');
  const found = (en as Record<string, Record<string, string>>)[section]?.[name];
  if (found === undefined) throw new Error(`no English string for '${key}'`);
  return found;
}

describe('feedbackLabel', () => {
  it('invites a rating when none has been given', () => {
    expect(said(feedbackLabel('up', null))).toBe('Rate response as helpful');
    expect(said(feedbackLabel('down', null))).toBe('Rate response as not helpful');
  });

  it('says what was recorded, on the one that was chosen', () => {
    expect(said(feedbackLabel('up', 'up'))).toMatch(/rated this helpful/i);
  });

  it('does not invite an action the control will not perform', () => {
    // A rating is recorded once. Leaving "Rate response as not
    // helpful" on a disabled button promises something that cannot
    // happen, which is worse than saying nothing.
    expect(said(feedbackLabel('down', 'up'))).not.toMatch(/^Rate response/);
  });

  it('explains why the other one is closed', () => {
    expect(said(feedbackLabel('down', 'up'))).toMatch(/already|once|recorded/i);
  });

  it('reads the same whichever way it was rated', () => {
    expect(said(feedbackLabel('up', 'down'))).toMatch(/already|once|recorded/i);
    expect(said(feedbackLabel('down', 'down'))).toMatch(/rated this unhelpful/i);
  });
});

describe('forkLabel', () => {
  it('invites the action when nothing is wrong', () => {
    expect(said(forkLabel({ busy: false, failed: false }))).toMatch(/branch a new conversation/i);
  });

  it('says a fork is under way', () => {
    expect(said(forkLabel({ busy: true, failed: false }))).toMatch(/branching|under way|in progress/i);
  });

  it('says it failed, not just in the tooltip', () => {
    // The title already changed on failure and the accessible name
    // did not, so the failure was visible only to people who could
    // see the tooltip.
    expect(said(forkLabel({ busy: false, failed: true }))).toMatch(/failed/i);
  });

  it('says what to do about a failure', () => {
    expect(said(forkLabel({ busy: false, failed: true }))).toMatch(/try again/i);
  });

  it('reports being busy even after an earlier failure', () => {
    expect(said(forkLabel({ busy: true, failed: true }))).toMatch(/branching|under way|in progress/i);
  });

  it('asks for the second click in words, not just a changed icon', () => {
    expect(said(forkLabel({ busy: false, failed: false, asking: true }))).toMatch(
      /fork from here/i,
    );
  });

  it('says what the second click will do', () => {
    expect(said(forkLabel({ busy: false, failed: false, asking: true }))).toMatch(
      /again|confirm/i,
    );
  });

  it('does not ask while a fork is already under way', () => {
    expect(said(forkLabel({ busy: true, failed: false, asking: true }))).toMatch(
      /branching|under way|in progress/i,
    );
  });
});

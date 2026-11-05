import { describe, expect, it } from 'vitest';

import { presentFollowups } from '@/lib/followups-view';

const offered = {
  offered: [
    { text: 'Show the trend over the year', because: 'expenses' },
    { text: 'Who approves these?', because: 'expenses' },
  ],
  setAside: 1,
  reason: '',
};

describe('presentFollowups', () => {
  it('shows nothing when there is nothing to suggest', () => {
    expect(presentFollowups({ offered: [], setAside: 0, reason: '' })).toBeNull();
  });

  it('shows nothing while part of the answer is missing', () => {
    const blocked = {
      offered: [],
      setAside: 3,
      reason: 'part of the question is still unanswered',
    };
    expect(presentFollowups(blocked)).toBeNull();
  });

  it('introduces the suggestions without overclaiming', () => {
    expect(presentFollowups(offered)?.prompt).toBe('You could ask next');
  });

  it('shows each suggestion as a chip', () => {
    expect(presentFollowups(offered)?.chips.map((c) => c.text)).toEqual([
      'Show the trend over the year',
      'Who approves these?',
    ]);
  });

  it('keeps why each was suggested for a tooltip', () => {
    expect(presentFollowups(offered)?.chips[0].because).toBe('about expenses');
  });

  it('marks chips as suggestions rather than commitments', () => {
    expect(presentFollowups(offered)?.chips[0].guaranteed).toBe(false);
  });

  it('does not mention what was set aside', () => {
    // Nobody needs to know which suggestions were discarded.
    const shown = presentFollowups(offered);
    expect(JSON.stringify(shown)).not.toContain('setAside');
  });

  it('is dismissible', () => {
    expect(presentFollowups(offered)?.dismissible).toBe(true);
  });

  it('does not take focus from the message box', () => {
    expect(presentFollowups(offered)?.takesFocus).toBe(false);
  });

  it('shows at most what it was given', () => {
    const one = { ...offered, offered: [offered.offered[0]] };
    expect(presentFollowups(one)?.chips).toHaveLength(1);
  });

  it('trims a suggestion that is too long to read at a glance', () => {
    const wordy = {
      ...offered,
      offered: [{ text: 'x'.repeat(100), because: 'expenses' }],
    };
    expect(presentFollowups(wordy)?.chips[0].text.length).toBeLessThanOrEqual(61);
  });

  it('keeps the full text for when it is clicked', () => {
    const wordy = {
      ...offered,
      offered: [{ text: 'x'.repeat(100), because: 'expenses' }],
    };
    expect(presentFollowups(wordy)?.chips[0].sends.length).toBe(100);
  });
});

import { describe, expect, it } from 'vitest';

import { presentDraft } from '@/lib/draft-recovery-view';

const offered = {
  outcome: 'offered' as const,
  text: 'half a question about the numbers',
  attachments: [] as string[],
  ageSeconds: 120,
  reason: 'saved 2 minutes ago',
};

describe('presentDraft', () => {
  it('shows nothing when there is no draft to offer', () => {
    const none = { ...offered, outcome: 'nothing-to-recover' as const, text: '' };
    expect(presentDraft(none)).toBeNull();
  });

  it('shows nothing when the draft was already sent', () => {
    const sent = { ...offered, outcome: 'already-sent' as const, text: '' };
    expect(presentDraft(sent)).toBeNull();
  });

  it('shows nothing for a draft too old to offer', () => {
    const stale = { ...offered, outcome: 'too-old' as const, text: '' };
    expect(presentDraft(stale)).toBeNull();
  });

  it('offers an unsent draft back', () => {
    expect(presentDraft(offered)?.headline).toBe('You have an unsent message here');
  });

  it('says when it was written', () => {
    expect(presentDraft(offered)?.detail).toBe('saved 2 minutes ago');
  });

  it('shows a preview of what was typed', () => {
    expect(presentDraft(offered)?.preview).toBe('half a question about the numbers');
  });

  it('shortens a long preview', () => {
    const long = { ...offered, text: 'x'.repeat(200) };
    expect(presentDraft(long)?.preview.length).toBeLessThanOrEqual(81);
  });

  it('mentions attachments that were waiting with it', () => {
    const withFile = { ...offered, attachments: ['report.pdf'] };
    expect(presentDraft(withFile)?.attachmentNote).toBe('1 attachment was waiting with it');
  });

  it('says nothing about attachments when there were none', () => {
    expect(presentDraft(offered)?.attachmentNote).toBe('');
  });

  it('lets the draft be restored', () => {
    expect(presentDraft(offered)?.action).toBe('restore');
  });

  it('lets the draft be thrown away', () => {
    expect(presentDraft(offered)?.secondaryAction).toBe('discard');
  });

  it('says plainly when the conversation it belonged to is gone', () => {
    const orphan = { ...offered, outcome: 'thread-gone' as const, reason: 'the conversation this belonged to is gone' };
    expect(presentDraft(orphan)?.headline).toBe('An unsent message survived a deleted conversation');
  });

  it('offers to copy rather than restore an orphaned draft', () => {
    const orphan = { ...offered, outcome: 'thread-gone' as const };
    expect(presentDraft(orphan)?.action).toBe('copy');
  });

  it('never discards without asking', () => {
    expect(presentDraft(offered)?.autoDiscards).toBe(false);
  });
});

import { describe, expect, it } from 'vitest';

import { presentHistory } from '@/lib/config-history-view';

const now = new Date('2026-10-27T09:00:00Z');

const revisions = [
  { version: 5, author: 'ana', at: '2026-09-17T09:00:00Z', changed: ['model'] },
  { version: 6, author: 'bo', at: '2026-10-25T09:00:00Z', changed: ['model'] },
  { version: 7, author: 'cy', at: '2026-10-27T08:00:00Z', changed: ['budget'] },
];

describe('presentHistory', () => {
  it('shows the newest revision first', () => {
    expect(presentHistory(revisions, now).rows[0].version).toBe(7);
  });

  it('marks the revision in force now', () => {
    expect(presentHistory(revisions, now).rows[0].current).toBe(true);
  });

  it('does not mark older revisions as current', () => {
    expect(presentHistory(revisions, now).rows[1].current).toBe(false);
  });

  it('says who made each change and when', () => {
    expect(presentHistory(revisions, now).rows[0].by).toBe('cy, 1 hour ago');
  });

  it('says nothing about what changed when it was not told', () => {
    // A history of one path is already about that path, so
    // "changed config/agent/PROMPT.md" on every row is noise.
    const unlabelled = [{ version: 1, author: 'ana', at: '2026-10-27T08:00:00Z' }];
    expect(presentHistory(unlabelled, now).rows[0].summary).toBe('');
  });

  it('says what each revision changed', () => {
    expect(presentHistory(revisions, now).rows[0].summary).toBe('changed budget');
  });

  it('names several changed settings', () => {
    const many = [{ ...revisions[0], changed: ['model', 'budget'] }];
    expect(presentHistory(many, now).rows[0].summary).toBe('changed model and budget');
  });

  it('offers to restore an older revision', () => {
    expect(presentHistory(revisions, now).rows[1].canRestore).toBe(true);
  });

  it('does not offer to restore what is already in force', () => {
    expect(presentHistory(revisions, now).rows[0].canRestore).toBe(false);
  });

  it('offers to restore an old revision as readily as a recent one', () => {
    // This used to refuse anything older than thirty days.
    // The agent has no such rule — it will restore any version
    // it still holds — so the limit existed only here: the
    // button was hidden while the capability remained, and
    // nobody could find the rule that hid it. One answer to
    // "can this be restored", and the agent gives it.
    expect(presentHistory(revisions, now).rows[2].canRestore).toBe(true);
  });

  it('has nothing to explain about an old revision', () => {
    expect(presentHistory(revisions, now).rows[2].note).toBe('');
  });

  it('warns that restoring creates a new revision rather than erasing one', () => {
    expect(presentHistory(revisions, now).restoreNote).toBe(
      'Restoring adds a new revision; nothing is erased',
    );
  });

  it('counts the revisions', () => {
    expect(presentHistory(revisions, now).count).toBe(3);
  });

  it('handles a single revision without offering a restore', () => {
    const only = presentHistory([revisions[2]], now);
    expect(only.rows[0].canRestore).toBe(false);
    expect(only.count).toBe(1);
  });

  it('says plainly when there is no history', () => {
    expect(presentHistory([], now).emptyMessage).toBe('No changes recorded');
  });
});

import { describe, expect, it } from 'vitest';

import { presentRetention } from '@/lib/retention-view';

const now = new Date('2026-10-27T09:00:00Z');

const retention = {
  action: 'keep' as const,
  deleteOn: '2027-01-24T09:00:00Z',
  warn: false,
  reason: '',
  pinned: false,
  onLegalHold: false,
};

describe('presentRetention', () => {
  it('says when the thread will be deleted', () => {
    expect(presentRetention(retention, now).label).toBe('Deletes on 24 January 2027');
  });

  it('says a thread with no deletion date is kept', () => {
    const forever = { ...retention, deleteOn: null };
    expect(presentRetention(forever, now).label).toBe('Kept indefinitely');
  });

  it('says a held thread is held rather than kept by chance', () => {
    const held = { ...retention, deleteOn: null, onLegalHold: true };
    expect(presentRetention(held, now).label).toBe('Kept while on legal hold');
  });

  it('says a held thread cannot be deleted by anyone', () => {
    const held = { ...retention, deleteOn: null, onLegalHold: true };
    expect(presentRetention(held, now).canDeleteNow).toBe(false);
  });

  it('lets an ordinary thread be deleted on request', () => {
    expect(presentRetention(retention, now).canDeleteNow).toBe(true);
  });

  it('counts down when deletion is near', () => {
    const soon = { ...retention, deleteOn: '2026-10-30T09:00:00Z', warn: true };
    expect(presentRetention(soon, now).label).toBe('Deletes in 3 days');
  });

  it('marks a near deletion so it can be shown differently', () => {
    const soon = { ...retention, deleteOn: '2026-10-30T09:00:00Z', warn: true };
    expect(presentRetention(soon, now).urgent).toBe(true);
  });

  it('does not mark a distant deletion as urgent', () => {
    expect(presentRetention(retention, now).urgent).toBe(false);
  });

  it('offers to pin a thread that is going to be deleted', () => {
    expect(presentRetention(retention, now).action).toBe('pin');
  });

  it('offers to unpin a pinned thread', () => {
    expect(presentRetention({ ...retention, pinned: true, deleteOn: null }, now).action).toBe(
      'unpin',
    );
  });

  it('offers nothing to change on a held thread', () => {
    const held = { ...retention, deleteOn: null, onLegalHold: true };
    expect(presentRetention(held, now).action).toBe('none');
  });

  it('says a pinned thread is kept because it is pinned', () => {
    const pinned = { ...retention, pinned: true, deleteOn: null };
    expect(presentRetention(pinned, now).label).toBe('Kept because it is pinned');
  });

  it('says an archived thread is archived without hiding the deletion date', () => {
    const archived = { ...retention, action: 'archive' as const };
    expect(presentRetention(archived, now).label).toBe('Archived, deletes on 24 January 2027');
  });

  it('says deletion happens today when it is due', () => {
    const due = { ...retention, deleteOn: '2026-10-27T18:00:00Z', warn: true };
    expect(presentRetention(due, now).label).toBe('Deletes today');
  });
});

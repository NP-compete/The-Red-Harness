import { describe, expect, it } from 'vitest';

import { presentBulkAction } from '@/lib/bulk-action-view';

const plan = {
  action: 'archive',
  count: 3,
  runnable: true,
  needsConfirmation: false,
  confirmation: '',
  reason: '',
  result: null,
};

describe('presentBulkAction', () => {
  it('says what will happen to how many', () => {
    expect(presentBulkAction(plan).headline).toBe('Archive 3 conversations');
  });

  it('uses the singular for one item', () => {
    expect(presentBulkAction({ ...plan, count: 1 }).headline).toBe('Archive 1 conversation');
  });

  it('can be run without confirming when it is small and reversible', () => {
    expect(presentBulkAction(plan).confirmFirst).toBe(false);
  });

  it('asks before a destructive action', () => {
    const destructive = {
      ...plan,
      action: 'delete',
      needsConfirmation: true,
      confirmation: 'delete 3 items?',
    };
    expect(presentBulkAction(destructive).confirmFirst).toBe(true);
  });

  it('shows the confirmation it was given', () => {
    const destructive = { ...plan, needsConfirmation: true, confirmation: 'delete 3 items?' };
    expect(presentBulkAction(destructive).confirmation).toBe('delete 3 items?');
  });

  it('cannot be run when nothing is selected', () => {
    const empty = { ...plan, count: 0, runnable: false, reason: 'there is nothing selected' };
    expect(presentBulkAction(empty).canRun).toBe(false);
  });

  it('says why it cannot be run', () => {
    const empty = { ...plan, count: 0, runnable: false, reason: 'there is nothing selected' };
    expect(presentBulkAction(empty).detail).toBe('there is nothing selected');
  });

  it('reports a finished run plainly', () => {
    const done = {
      ...plan,
      result: { done: 3, skipped: 0, failed: 0, failedItems: [], message: '3 done' },
    };
    expect(presentBulkAction(done).headline).toBe('3 done');
  });

  it('does not call a partial failure a success', () => {
    const partial = {
      ...plan,
      result: { done: 2, skipped: 0, failed: 1, failedItems: ['c'], message: '2 done, 1 failed' },
    };
    expect(presentBulkAction(partial).succeeded).toBe(false);
  });

  it('offers to retry only the ones that failed', () => {
    const partial = {
      ...plan,
      result: { done: 2, skipped: 0, failed: 1, failedItems: ['c'], message: '2 done, 1 failed' },
    };
    expect(presentBulkAction(partial).retryItems).toEqual(['c']);
  });

  it('offers no retry when everything worked', () => {
    const done = {
      ...plan,
      result: { done: 3, skipped: 0, failed: 0, failedItems: [], message: '3 done' },
    };
    expect(presentBulkAction(done).retryItems).toEqual([]);
  });

  it('treats a partial failure as worth noticing', () => {
    const partial = {
      ...plan,
      result: { done: 2, skipped: 0, failed: 1, failedItems: ['c'], message: '2 done, 1 failed' },
    };
    expect(presentBulkAction(partial).severity).toBe('medium');
  });

  it('treats a clean run as unremarkable', () => {
    const done = {
      ...plan,
      result: { done: 3, skipped: 0, failed: 0, failedItems: [], message: '3 done' },
    };
    expect(presentBulkAction(done).severity).toBe('none');
  });
});

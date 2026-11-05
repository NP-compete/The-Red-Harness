import { describe, expect, it } from 'vitest';

import { presentRequest } from '@/lib/subject-request-view';

const now = new Date('2026-10-27T09:00:00Z');

const request = {
  kind: 'delete' as const,
  included: ['threads'],
  withheld: { audit: 'kept as a record', memories: 'under legal hold' },
  complete: false,
  dueAt: '2026-11-26T09:00:00Z',
  notice: 'data remains in audit, memories',
  state: 'planned' as const,
};

describe('presentRequest', () => {
  it('says what was asked for', () => {
    expect(presentRequest(request, now).headline).toBe('Request to delete your data');
  });

  it('says what an export was asked for', () => {
    const exportRequest = { ...request, kind: 'export' as const, complete: true, withheld: {} };
    expect(presentRequest(exportRequest, now).headline).toBe('Request to export your data');
  });

  it('lists where the request will be carried out', () => {
    expect(presentRequest(request, now).covered).toEqual(['threads']);
  });

  it('explains each place it will not be', () => {
    expect(presentRequest(request, now).exceptions).toEqual([
      { place: 'audit', reason: 'kept as a record' },
      { place: 'memories', reason: 'under legal hold' },
    ]);
  });

  it('says plainly that the request cannot be fully met', () => {
    expect(presentRequest(request, now).warning).toBe('data remains in audit, memories');
  });

  it('has no warning when everything can be done', () => {
    const whole = { ...request, complete: true, withheld: {}, notice: '' };
    expect(presentRequest(whole, now).warning).toBe('');
  });

  it('says when the request is due', () => {
    expect(presentRequest(request, now).due).toBe('due in 30 days');
  });

  it('says plainly when the deadline has passed', () => {
    const late = { ...request, dueAt: '2026-10-20T09:00:00Z' };
    expect(presentRequest(late, now).due).toBe('overdue');
  });

  it('treats an overdue request as serious', () => {
    const late = { ...request, dueAt: '2026-10-20T09:00:00Z' };
    expect(presentRequest(late, now).severity).toBe('high');
  });

  it('treats a partial deletion as worth reading carefully', () => {
    expect(presentRequest(request, now).severity).toBe('medium');
  });

  it('treats a straightforward request as routine', () => {
    const whole = { ...request, complete: true, withheld: {}, notice: '' };
    expect(presentRequest(whole, now).severity).toBe('info');
  });

  it('needs confirming before a deletion starts', () => {
    expect(presentRequest(request, now).confirmFirst).toBe(true);
  });

  it('does not need confirming for an export', () => {
    const exportRequest = { ...request, kind: 'export' as const };
    expect(presentRequest(exportRequest, now).confirmFirst).toBe(false);
  });

  it('shows a finished request as done rather than pending', () => {
    const done = { ...request, state: 'done' as const };
    expect(presentRequest(done, now).due).toBe('completed');
  });

  it('offers nothing to confirm once it is done', () => {
    const done = { ...request, state: 'done' as const };
    expect(presentRequest(done, now).confirmFirst).toBe(false);
  });
});

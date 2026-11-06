import { describe, expect, it } from 'vitest';

import { presentApprovalQueue } from '@/lib/approval-queue';

const now = new Date('2026-10-27T09:00:00Z');

const pending = {
  id: 'ap-1',
  tool: 'deploy',
  summary: 'Deploy release 4.2 to production',
  requestedBy: 'the finance agent',
  requestedAt: '2026-10-27T08:55:00Z',
  expiresAt: '2026-10-27T09:25:00Z',
  eligibleApprovers: ['bo', 'cy'],
  requesterId: 'ana',
};

describe('presentApprovalQueue', () => {
  it('says how long is left to decide', () => {
    const [shown] = presentApprovalQueue([pending], { now, viewerId: 'bo' });
    expect(shown.timeLeft).toBe('25 minutes left');
  });

  it('lets an eligible approver act', () => {
    const [shown] = presentApprovalQueue([pending], { now, viewerId: 'bo' });
    expect(shown.canAct).toBe(true);
  });

  it('does not let a bystander act', () => {
    const [shown] = presentApprovalQueue([pending], { now, viewerId: 'dee' });
    expect(shown.canAct).toBe(false);
  });

  it('tells a bystander who can act instead', () => {
    const [shown] = presentApprovalQueue([pending], { now, viewerId: 'dee' });
    expect(shown.blockedReason).toBe('Waiting on bo or cy.');
  });

  it('does not let the requester approve their own request', () => {
    const [shown] = presentApprovalQueue([pending], { now, viewerId: 'ana' });
    expect(shown.canAct).toBe(false);
  });

  it('tells the requester why they cannot approve', () => {
    const [shown] = presentApprovalQueue([pending], { now, viewerId: 'ana' });
    expect(shown.blockedReason).toContain('your own request');
  });

  it('still lets the requester withdraw', () => {
    const [shown] = presentApprovalQueue([pending], { now, viewerId: 'ana' });
    expect(shown.canWithdraw).toBe(true);
  });

  it('does not offer withdrawal to anyone else', () => {
    const [shown] = presentApprovalQueue([pending], { now, viewerId: 'bo' });
    expect(shown.canWithdraw).toBe(false);
  });

  it('marks a request that is running out of time', () => {
    const soon = { ...pending, expiresAt: '2026-10-27T09:02:00Z' };
    expect(presentApprovalQueue([soon], { now, viewerId: 'bo' })[0].urgent).toBe(true);
  });

  it('does not mark a request with plenty of time', () => {
    expect(presentApprovalQueue([pending], { now, viewerId: 'bo' })[0].urgent).toBe(false);
  });

  it('shows an expired request as expired, not as waiting', () => {
    const stale = { ...pending, expiresAt: '2026-10-27T08:59:00Z' };
    const [shown] = presentApprovalQueue([stale], { now, viewerId: 'bo' });
    expect(shown.timeLeft).toBe('expired');
    expect(shown.canAct).toBe(false);
  });

  it('says an expired request did not go ahead', () => {
    const stale = { ...pending, expiresAt: '2026-10-27T08:59:00Z' };
    const [shown] = presentApprovalQueue([stale], { now, viewerId: 'bo' });
    expect(shown.blockedReason).toContain('did not go ahead');
  });

  it('puts the most urgent request first', () => {
    const soon = { ...pending, id: 'ap-2', expiresAt: '2026-10-27T09:02:00Z' };
    const queue = presentApprovalQueue([pending, soon], { now, viewerId: 'bo' });
    expect(queue.map((item) => item.id)).toEqual(['ap-2', 'ap-1']);
  });

  it('sinks expired requests below ones that can still be answered', () => {
    const stale = { ...pending, id: 'ap-0', expiresAt: '2026-10-27T08:59:00Z' };
    const queue = presentApprovalQueue([stale, pending], { now, viewerId: 'bo' });
    expect(queue.map((item) => item.id)).toEqual(['ap-1', 'ap-0']);
  });

  it('keeps the plain summary rather than the tool name', () => {
    const [shown] = presentApprovalQueue([pending], { now, viewerId: 'bo' });
    expect(shown.title).toBe('Deploy release 4.2 to production');
  });

  it('shows an empty queue as empty', () => {
    expect(presentApprovalQueue([], { now, viewerId: 'bo' })).toEqual([]);
  });
});

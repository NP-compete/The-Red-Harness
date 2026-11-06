import { describe, expect, it } from 'vitest';

import { presentDeadLetters } from '@/lib/dead-letter-view';

const now = new Date('2026-10-27T09:00:00Z');

const items = [
  {
    deliveryId: 'd1',
    destination: 'issue-tracker',
    reason: 'all 5 attempts failed: timeout',
    replayable: true,
    parkedAt: '2026-10-27T08:00:00Z',
  },
  {
    deliveryId: 'd2',
    destination: 'issue-tracker',
    reason: 'all 5 attempts failed: timeout',
    replayable: true,
    parkedAt: '2026-10-27T08:30:00Z',
  },
  {
    deliveryId: 'd3',
    destination: 'mail',
    reason: 'the destination refused this: unknown recipient',
    replayable: false,
    parkedAt: '2026-10-27T07:00:00Z',
  },
];

describe('presentDeadLetters', () => {
  it('groups failures by where they were going', () => {
    expect(presentDeadLetters(items, now).groups.map((group) => group.destination)).toEqual([
      'issue-tracker',
      'mail',
    ]);
  });

  it('counts the failures per destination', () => {
    expect(presentDeadLetters(items, now).groups[0].count).toBe(2);
  });

  it('puts the destination with most failures first', () => {
    expect(presentDeadLetters(items, now).groups[0].destination).toBe('issue-tracker');
  });

  it('shows the shared reason once rather than per item', () => {
    expect(presentDeadLetters(items, now).groups[0].reason).toBe('all 5 attempts failed: timeout');
  });

  it('says when the most recent one was parked', () => {
    expect(presentDeadLetters(items, now).groups[0].latest).toBe('30 minutes ago');
  });

  it('offers to replay a group that can be replayed', () => {
    expect(presentDeadLetters(items, now).groups[0].action).toBe('replay');
  });

  it('offers no replay for something the destination refused', () => {
    expect(presentDeadLetters(items, now).groups[1].action).toBe('discard');
  });

  it('explains why a refused delivery will not be replayed', () => {
    expect(presentDeadLetters(items, now).groups[1].note).toBe(
      'Replaying this would be refused again',
    );
  });

  it('adds no such note to a replayable group', () => {
    expect(presentDeadLetters(items, now).groups[0].note).toBe('');
  });

  it('totals everything set aside', () => {
    expect(presentDeadLetters(items, now).total).toBe(3);
  });

  it('counts only what can actually be replayed', () => {
    expect(presentDeadLetters(items, now).replayable).toBe(2);
  });

  it('says plainly when nothing has been set aside', () => {
    expect(presentDeadLetters([], now).emptyMessage).toBe('Nothing has failed delivery');
  });

  it('does not split one destination across groups by reason', () => {
    const mixed = [...items, { ...items[0], deliveryId: 'd4', reason: 'something else' }];
    expect(presentDeadLetters(mixed, now).groups).toHaveLength(2);
  });
});

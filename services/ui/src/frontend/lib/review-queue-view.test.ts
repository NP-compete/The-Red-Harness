import { describe, expect, it } from 'vitest';

import { presentReviewQueue } from '@/lib/review-queue-view';

const now = new Date('2026-10-27T09:00:00Z');

const sample = [
  {
    runId: 'r1',
    outcome: 'failed' as const,
    ratedDown: false,
    at: '2026-10-27T08:00:00Z',
    reviewedBy: null as string | null,
    verdict: null as 'good' | 'bad' | null,
  },
  {
    runId: 'r2',
    outcome: 'ok' as const,
    ratedDown: true,
    at: '2026-10-27T07:00:00Z',
    reviewedBy: null as string | null,
    verdict: null as 'good' | 'bad' | null,
  },
  {
    runId: 'r3',
    outcome: 'ok' as const,
    ratedDown: false,
    at: '2026-10-27T06:00:00Z',
    reviewedBy: 'ana',
    verdict: 'good' as const,
  },
];

const row = (id: string) =>
  presentReviewQueue(sample, now).rows.find((candidate) => candidate.runId === id)!;

describe('presentReviewQueue', () => {
  it('says why each run was picked', () => {
    expect(row('r1').because).toBe('it failed');
  });

  it('says when a run was picked because someone disliked it', () => {
    expect(row('r2').because).toBe('someone rated it down');
  });

  it('says plainly when a run is just a sample of normal', () => {
    expect(row('r3').because).toBe('a sample of ordinary runs');
  });

  it('puts unreviewed runs before reviewed ones', () => {
    expect(presentReviewQueue(sample, now).rows.at(-1)?.runId).toBe('r3');
  });

  it('shows who reviewed a run that has been looked at', () => {
    expect(row('r3').status).toBe('reviewed by ana');
  });

  it('shows a run nobody has looked at as waiting', () => {
    expect(row('r1').status).toBe('waiting');
  });

  it('counts how much is left to do', () => {
    expect(presentReviewQueue(sample, now).remaining).toBe(2);
  });

  it('shows progress through the sample', () => {
    expect(presentReviewQueue(sample, now).progress).toBe('1 of 3 reviewed');
  });

  it('says how long ago each run happened', () => {
    expect(row('r1').when).toBe('1 hour ago');
  });

  it('lets an unreviewed run be judged', () => {
    expect(row('r1').action).toBe('review');
  });

  it('lets a reviewed run be looked at again rather than locking it', () => {
    expect(row('r3').action).toBe('reopen');
  });

  it('reports the verdicts so far', () => {
    expect(presentReviewQueue(sample, now).verdicts).toEqual({ good: 1, bad: 0 });
  });

  it('does not claim a result while most of the sample is unreviewed', () => {
    expect(presentReviewQueue(sample, now).conclusion).toBe('');
  });

  it('gives a conclusion once the sample is done', () => {
    const done = sample.map((run) => ({ ...run, reviewedBy: 'ana', verdict: 'good' as const }));
    expect(presentReviewQueue(done, now).conclusion).toBe('3 of 3 judged good');
  });

  it('says plainly when there is nothing to review', () => {
    expect(presentReviewQueue([], now).emptyMessage).toBe('Nothing to review');
  });
});

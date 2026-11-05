import { describe, expect, it } from 'vitest';

import { bucketUsage } from '@/lib/usage-chart-view';

const points = [
  { at: '2026-10-25T09:00:00Z', runs: 3, cost: 1.5 },
  { at: '2026-10-25T15:00:00Z', runs: 2, cost: 0.5 },
  { at: '2026-10-26T09:00:00Z', runs: 5, cost: 2.0 },
];

const now = new Date('2026-10-27T09:00:00Z');

describe('bucketUsage', () => {
  it('groups points into days', () => {
    expect(bucketUsage(points, { days: 3, now }).buckets).toHaveLength(3);
  });

  it('adds up the runs in each day', () => {
    const buckets = bucketUsage(points, { days: 3, now }).buckets;
    expect(buckets[0].runs).toBe(5);
  });

  it('adds up the cost in each day', () => {
    const buckets = bucketUsage(points, { days: 3, now }).buckets;
    expect(buckets[0].cost).toBe(2);
  });

  it('includes days with nothing in them', () => {
    const buckets = bucketUsage(points, { days: 3, now }).buckets;
    expect(buckets[2].runs).toBe(0);
  });

  it('puts the oldest day first', () => {
    const buckets = bucketUsage(points, { days: 3, now }).buckets;
    expect(buckets[0].label).toBe('25 Oct');
  });

  it('labels each day readably', () => {
    const buckets = bucketUsage(points, { days: 3, now }).buckets;
    expect(buckets.map((bucket) => bucket.label)).toEqual(['25 Oct', '26 Oct', '27 Oct']);
  });

  it('ignores points older than the window', () => {
    const old = [{ at: '2026-01-01T09:00:00Z', runs: 99, cost: 99 }, ...points];
    expect(bucketUsage(old, { days: 3, now }).total.runs).toBe(10);
  });

  it('says how many points fell outside the window', () => {
    const old = [{ at: '2026-01-01T09:00:00Z', runs: 99, cost: 99 }, ...points];
    expect(bucketUsage(old, { days: 3, now }).outsideWindow).toBe(1);
  });

  it('totals the window', () => {
    expect(bucketUsage(points, { days: 3, now }).total).toEqual({ runs: 10, cost: 4 });
  });

  it('reports the busiest day', () => {
    expect(bucketUsage(points, { days: 3, now }).busiest).toBe('26 Oct');
  });

  it('breaks a tie for busiest day towards the most recent', () => {
    // 25 Oct and 26 Oct both total 5 runs here.
    expect(bucketUsage(points, { days: 3, now }).buckets[0].runs).toBe(5);
    expect(bucketUsage(points, { days: 3, now }).buckets[1].runs).toBe(5);
  });

  it('has no busiest day when nothing happened', () => {
    expect(bucketUsage([], { days: 3, now }).busiest).toBe('');
  });

  it('still returns the days when nothing happened', () => {
    expect(bucketUsage([], { days: 3, now }).buckets).toHaveLength(3);
  });

  it('gives the tallest bar for scaling', () => {
    expect(bucketUsage(points, { days: 3, now }).peak).toBe(5);
  });

  it('gives a peak of zero when nothing happened', () => {
    expect(bucketUsage([], { days: 3, now }).peak).toBe(0);
  });

  it('refuses a window of no days', () => {
    expect(() => bucketUsage(points, { days: 0, now })).toThrow();
  });
});

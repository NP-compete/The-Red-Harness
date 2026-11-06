import { describe, expect, it } from 'vitest';

import { presentAnnotationQueue } from '@/lib/annotation-queue-view';

const entries = [
  { item: 'q2', reason: 'flagged' as const },
  { item: 'q1', reason: 'disagreement' as const },
];

describe('presentAnnotationQueue', () => {
  it('says how many items need a person', () => {
    expect(presentAnnotationQueue(entries).headline).toBe('2 items need review');
  });

  it('counts a single item in the singular', () => {
    expect(presentAnnotationQueue([entries[0]]).headline).toBe('1 item needs review');
  });

  it('keeps the order it was given', () => {
    expect(presentAnnotationQueue(entries).rows.map((r) => r.item)).toEqual(['q2', 'q1']);
  });

  it('says in plain words why something was flagged', () => {
    expect(presentAnnotationQueue(entries).rows[0].why).toBe('Someone asked for another look');
  });

  it('says in plain words why graders disagreed', () => {
    expect(presentAnnotationQueue(entries).rows[1].why).toBe('The graders disagreed');
  });

  it('explains an unsure grade', () => {
    const unsure = [{ item: 'q3', reason: 'low_confidence' as const }];
    expect(presentAnnotationQueue(unsure).rows[0].why).toBe('The grade was not a confident one');
  });

  it('explains a failure', () => {
    const failed = [{ item: 'q4', reason: 'failed' as const }];
    expect(presentAnnotationQueue(failed).rows[0].why).toBe('This item did not pass');
  });

  it('says nothing is waiting when the queue is empty', () => {
    expect(presentAnnotationQueue([]).headline).toBe('Nothing needs review');
  });

  it('has no rows when the queue is empty', () => {
    expect(presentAnnotationQueue([]).rows).toEqual([]);
  });

  it('is worth attention while anything is waiting', () => {
    expect(presentAnnotationQueue(entries).needsAttention).toBe(true);
  });

  it('is not worth attention when the queue is clear', () => {
    expect(presentAnnotationQueue([]).needsAttention).toBe(false);
  });
});

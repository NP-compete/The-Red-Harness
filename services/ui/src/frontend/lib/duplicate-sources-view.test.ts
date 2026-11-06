import { describe, expect, it } from 'vitest';

import { presentSourceList } from '@/lib/duplicate-sources-view';

const kept = [
  {
    source: 'policy',
    text: 'Expenses over 500 need approval.',
    score: 0.9,
    authority: 'policy',
    alsoIn: ['handbook', 'wiki'],
    corroborated: true,
  },
  {
    source: 'notes',
    text: 'Travel is booked centrally.',
    score: 0.4,
    authority: 'note',
    alsoIn: [] as string[],
    corroborated: false,
  },
];

describe('presentSourceList', () => {
  it('lists each distinct passage once', () => {
    expect(presentSourceList(kept, 2).rows).toHaveLength(2);
  });

  it('says when other sources say the same thing', () => {
    expect(presentSourceList(kept, 2).rows[0].agreement).toBe('also in handbook and wiki');
  });

  it('says nothing about agreement for a lone source', () => {
    expect(presentSourceList(kept, 2).rows[1].agreement).toBe('');
  });

  it('marks a corroborated passage as more trustworthy', () => {
    expect(presentSourceList(kept, 2).rows[0].confidence).toBe('corroborated');
  });

  it('marks a single-source passage as such', () => {
    expect(presentSourceList(kept, 2).rows[1].confidence).toBe('single source');
  });

  it('warns about a passage resting on notes alone', () => {
    expect(presentSourceList(kept, 2).rows[1].warning).toBe(
      'This rests on one informal source',
    );
  });

  it('does not warn about a corroborated policy', () => {
    expect(presentSourceList(kept, 2).rows[0].warning).toBe('');
  });

  it('does not warn about a lone authoritative source', () => {
    const lone = [{ ...kept[0], alsoIn: [], corroborated: false }];
    expect(presentSourceList(lone, 1).rows[0].warning).toBe('');
  });

  it('says how many repeats were folded away', () => {
    expect(presentSourceList(kept, 2).note).toBe('2 repeated passages were folded in');
  });

  it('uses the singular for one repeat', () => {
    expect(presentSourceList(kept, 1).note).toBe('1 repeated passage was folded in');
  });

  it('says nothing when there were no repeats', () => {
    expect(presentSourceList(kept, 0).note).toBe('');
  });

  it('keeps the order it was given', () => {
    expect(presentSourceList(kept, 0).rows.map((row) => row.source)).toEqual(['policy', 'notes']);
  });

  it('says plainly when there are no sources at all', () => {
    expect(presentSourceList([], 0).emptyMessage).toBe('No sources were used');
  });

  it('has no empty message when there are sources', () => {
    expect(presentSourceList(kept, 0).emptyMessage).toBe('');
  });
});

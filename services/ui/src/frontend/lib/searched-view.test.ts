/**
 * What the search weighed, for somebody asking why it missed.
 *
 * "Your document was not used" covers three different problems
 * with three different fixes: it was out of scope, it shared no
 * words with the question, or it scored just under the
 * threshold somebody set. Only the last leaves a row here, and
 * seeing that row is the difference between changing a setting
 * and giving up.
 *
 * Which is also why the near misses lead. The documents that
 * were used are already named in the citations above; repeating
 * them first would bury the only new thing on the strip.
 */

import { describe, expect, it } from 'vitest';

import { describeSearched, type SearchedRecord } from './searched-view';

const used: SearchedRecord = {
  id: 'strong',
  title: 'Spending limits',
  scope: 'user',
  score: 1,
  used: true,
};

const missed: SearchedRecord = {
  id: 'weak',
  title: 'Old notes',
  scope: 'user',
  score: 0.33,
  used: false,
};

describe('when there is nothing to show', () => {
  it('nothing for an answer that searched nothing', () => {
    expect(describeSearched(undefined)).toBeNull();
  });

  it('nothing for an empty record', () => {
    // An empty strip reads as "looked and found none", which
    // is a different claim from "did not need to look".
    expect(describeSearched([])).toBeNull();
  });

  it('nothing for a shape it does not recognise', () => {
    expect(describeSearched('not a list' as never)).toBeNull();
  });
});

describe('what comes back', () => {
  it('counts what was used', () => {
    expect(describeSearched([used, missed])?.usedCount).toBe(1);
  });

  it('counts what nearly was', () => {
    expect(describeSearched([used, missed])?.missedCount).toBe(1);
  });

  it('puts the near misses first', () => {
    // The used ones are already named in the citations above.
    // Repeating them first buries the only new thing here.
    expect(describeSearched([used, missed])?.rows[0].id).toBe('weak');
  });

  it('keeps the used ones too', () => {
    expect(describeSearched([used, missed])?.rows).toHaveLength(2);
  });

  it('ranks within a group by score', () => {
    const weaker = { ...missed, id: 'weaker', score: 0.1 };
    const found = describeSearched([weaker, missed, used]);
    expect(found?.rows.map((row) => row.id)).toEqual(['weak', 'weaker', 'strong']);
  });
});

describe('the score as somebody reads it', () => {
  it('is a percentage, not a decimal nobody can compare', () => {
    expect(describeSearched([used])?.rows[0].match).toBe('100%');
  });

  it('rounds rather than inventing precision', () => {
    expect(describeSearched([missed])?.rows[0].match).toBe('33%');
  });

  it('survives a score that is missing', () => {
    const odd = { ...used, score: undefined as never };
    expect(describeSearched([odd])?.rows[0].match).toBe('—');
  });

  it('survives a score that is not a number', () => {
    const odd = { ...used, score: 'high' as never };
    expect(describeSearched([odd])?.rows[0].match).toBe('—');
  });
});

describe('a document with no title', () => {
  it('falls back to its identifier rather than showing a blank', () => {
    const nameless = { ...used, title: '' };
    expect(describeSearched([nameless])?.rows[0].title).toBe('strong');
  });
});

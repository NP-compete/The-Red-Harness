import { describe, expect, it } from 'vitest';

import { presentSearchExplanation } from '@/lib/search-explain-view';

const explanation = {
  original: 'could you please tell me about pto policy',
  query: 'pto policy paid time off annual leave',
  expanded: ['pto'],
  removed: ['could', 'you', 'please', 'tell', 'me', 'about'],
  tooVague: false,
  resultCount: 7,
};

describe('presentSearchExplanation', () => {
  it('says what was actually searched for', () => {
    expect(presentSearchExplanation(explanation).searched).toBe(
      'pto policy paid time off annual leave',
    );
  });

  it('explains an expansion in plain words', () => {
    expect(presentSearchExplanation(explanation).notes).toContain(
      'also searched for what pto stands for',
    );
  });

  it('mentions removed filler without listing every word', () => {
    expect(presentSearchExplanation(explanation).notes).toContain('ignored 6 common words');
  });

  it('says nothing about filler when none was removed', () => {
    const plain = { ...explanation, removed: [], expanded: [] };
    expect(presentSearchExplanation(plain).notes).toEqual([]);
  });

  it('warns when the question was too vague to search well', () => {
    const vague = { ...explanation, tooVague: true, resultCount: 0 };
    expect(presentSearchExplanation(vague).warning).toBe(
      'That was a bit vague — try naming what you are looking for',
    );
  });

  it('does not warn about an ordinary question', () => {
    expect(presentSearchExplanation(explanation).warning).toBe('');
  });

  it('says how many results were found', () => {
    expect(presentSearchExplanation(explanation).summary).toBe('7 results');
  });

  it('uses the singular for one result', () => {
    expect(presentSearchExplanation({ ...explanation, resultCount: 1 }).summary).toBe('1 result');
  });

  it('says plainly when nothing was found', () => {
    const empty = { ...explanation, resultCount: 0 };
    expect(presentSearchExplanation(empty).summary).toBe('Nothing found');
  });

  it('suggests dropping the expansion when nothing was found', () => {
    const empty = { ...explanation, resultCount: 0 };
    expect(presentSearchExplanation(empty).action).toBe('search-exact');
  });

  it('offers nothing to change when results were found', () => {
    expect(presentSearchExplanation(explanation).action).toBe('none');
  });

  it('keeps the original wording available', () => {
    expect(presentSearchExplanation(explanation).original).toBe(
      'could you please tell me about pto policy',
    );
  });

  it('is collapsed by default so it does not crowd the results', () => {
    expect(presentSearchExplanation(explanation).openByDefault).toBe(false);
  });

  it('opens itself when nothing was found', () => {
    const empty = { ...explanation, resultCount: 0 };
    expect(presentSearchExplanation(empty).openByDefault).toBe(true);
  });
});

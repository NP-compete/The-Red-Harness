import { describe, expect, it } from 'vitest';

import { presentQuote } from '@/lib/quote-view';

const quote = {
  source: 'handbook',
  text: 'The limit is 500 euros.',
  offset: 31,
  shortened: false,
};

describe('presentQuote', () => {
  it('shows the quoted words', () => {
    expect(presentQuote(quote)?.text).toBe('The limit is 500 euros.');
  });

  it('names where the words came from', () => {
    expect(presentQuote(quote)?.source).toBe('handbook');
  });

  it('marks a shortened quote so no one reads it as the whole sentence', () => {
    expect(presentQuote({ ...quote, shortened: true })?.text).toBe(
      '…The limit is 500 euros.…',
    );
  });

  it('does not mark an unshortened quote', () => {
    expect(presentQuote(quote)?.text).toBe('The limit is 500 euros.');
  });

  it('offers a way to open the source at the right place', () => {
    expect(presentQuote(quote)?.jumpTo).toBe(31);
  });

  it('says nothing when there is no evidence to show', () => {
    expect(presentQuote(null)).toBeNull();
  });

  it('says plainly that a shortened quote has more around it', () => {
    expect(presentQuote({ ...quote, shortened: true })?.note).toBe('Shortened from the original');
  });

  it('adds no note to a whole quote', () => {
    expect(presentQuote(quote)?.note).toBe('');
  });
});

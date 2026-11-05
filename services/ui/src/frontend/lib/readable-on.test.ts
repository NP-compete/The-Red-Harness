import { describe, expect, it } from 'vitest';

import { contrastRatio, readableOn } from './readable-on';

describe('contrastRatio', () => {
  it('is 21 for black on white', () => {
    expect(Math.round(contrastRatio('#000000', '#ffffff'))).toBe(21);
  });

  it('is 1 for a colour against itself', () => {
    expect(contrastRatio('#0066cc', '#0066cc')).toBeCloseTo(1, 5);
  });

  it('does not care which way round the pair is given', () => {
    expect(contrastRatio('#0066cc', '#ffffff')).toBeCloseTo(
      contrastRatio('#ffffff', '#0066cc'),
      5,
    );
  });
});

describe('readableOn', () => {
  it('puts light text on a dark brand colour', () => {
    expect(readableOn('#0066cc')).toBe('#ffffff');
  });

  it('puts dark text on a light brand colour', () => {
    // The dark theme's blue is light; white on it was 2.24 to 1.
    expect(readableOn('#4dabf7')).toBe('#0f1117');
  });

  it('clears the bar for both brand colours', () => {
    for (const brand of ['#0066cc', '#4dabf7']) {
      expect(contrastRatio(readableOn(brand), brand)).toBeGreaterThanOrEqual(4.5);
    }
  });

  it('copes with a three-digit colour', () => {
    expect(readableOn('#06c')).toBe('#ffffff');
  });

  it('copes with a colour it cannot read, rather than guessing', () => {
    expect(readableOn('not a colour')).toBe('#ffffff');
  });

  it('picks the better of the two when neither is ideal', () => {
    const mid = '#767676';
    const chosen = readableOn(mid);
    const other = chosen === '#ffffff' ? '#0f1117' : '#ffffff';
    expect(contrastRatio(chosen, mid)).toBeGreaterThanOrEqual(contrastRatio(other, mid));
  });
});

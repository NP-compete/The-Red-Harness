import { describe, expect, it } from 'vitest';

import { presentResponseTiming } from './response-timing';

const took = { totalDurationMs: 9100, timeToFirstTokenMs: 2872 };

describe('presentResponseTiming', () => {
  it('says how long a finished answer took', () => {
    expect(presentResponseTiming({ ...took, cutShort: false }).line).toContain('9.1s');
  });

  it('says when the first word arrived', () => {
    expect(presentResponseTiming({ ...took, cutShort: false }).firstToken).toContain(
      '2872',
    );
  });

  it('says nothing about a first word nobody measured', () => {
    expect(
      presentResponseTiming({ totalDurationMs: 9100, timeToFirstTokenMs: null, cutShort: false })
        .firstToken,
    ).toBe('');
  });

  it('says plainly that a cut answer stopped early', () => {
    // A timing footer on a reply that ends mid-sentence reads as a
    // reply that finished in that time.
    expect(presentResponseTiming({ ...took, cutShort: true }).line).toMatch(
      /stopped early|cut short|incomplete/i,
    );
  });

  it('still reports the time a cut answer ran for', () => {
    expect(presentResponseTiming({ ...took, cutShort: true }).line).toContain('9.1s');
  });

  it('reads the same aloud as it does on screen', () => {
    const cut = presentResponseTiming({ ...took, cutShort: true });
    expect(cut.spoken).toMatch(/stopped early|cut short|incomplete/i);
  });

  it('does not call a finished answer incomplete', () => {
    const done = presentResponseTiming({ ...took, cutShort: false });
    expect(done.line).not.toMatch(/stopped early|cut short|incomplete/i);
    expect(done.spoken).not.toMatch(/stopped early|cut short|incomplete/i);
  });

  it('speaks the duration in words rather than as punctuation', () => {
    expect(presentResponseTiming({ ...took, cutShort: false }).spoken).toMatch(
      /9\.1 seconds/,
    );
  });
});

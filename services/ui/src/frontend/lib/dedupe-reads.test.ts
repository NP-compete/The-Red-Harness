import { describe, expect, it } from 'vitest';

import { dedupeReads } from './dedupe-reads';

describe('dedupeReads', () => {
  it('keeps a single result as it is', () => {
    const { kept, collapsed } = dedupeReads([{ source: 'handbook', text: 'the limit is 500' }]);
    expect(kept).toHaveLength(1);
    expect(collapsed).toBe(0);
  });

  it('folds an identical result returned twice', () => {
    const { kept, collapsed } = dedupeReads([
      { source: 'handbook', text: 'the limit is 500' },
      { source: 'policy', text: 'the limit is 500' },
    ]);
    expect(kept).toHaveLength(1);
    expect(collapsed).toBe(1);
  });

  it('names the other place it was found', () => {
    const { kept } = dedupeReads([
      { source: 'handbook', text: 'the limit is 500' },
      { source: 'policy', text: 'the limit is 500' },
    ]);
    expect(kept[0].alsoIn).toEqual(['policy']);
  });

  it('treats two sources agreeing as corroboration', () => {
    const { kept } = dedupeReads([
      { source: 'handbook', text: 'the limit is 500' },
      { source: 'policy', text: 'the limit is 500' },
    ]);
    expect(kept[0].corroborated).toBe(true);
  });

  it('does not call a lone result corroborated', () => {
    const { kept } = dedupeReads([{ source: 'handbook', text: 'the limit is 500' }]);
    expect(kept[0].corroborated).toBe(false);
  });

  it('ignores differences of spacing when comparing', () => {
    const { collapsed } = dedupeReads([
      { source: 'handbook', text: 'the limit is 500' },
      { source: 'policy', text: '  the limit   is 500 ' },
    ]);
    expect(collapsed).toBe(1);
  });

  it('keeps genuinely different results apart', () => {
    const { kept, collapsed } = dedupeReads([
      { source: 'handbook', text: 'the limit is 500' },
      { source: 'policy', text: 'receipts within thirty days' },
    ]);
    expect(kept).toHaveLength(2);
    expect(collapsed).toBe(0);
  });

  it('does not count the same tool answering twice as corroboration', () => {
    // One source repeating itself is one source.
    const { kept } = dedupeReads([
      { source: 'handbook', text: 'the limit is 500' },
      { source: 'handbook', text: 'the limit is 500' },
    ]);
    expect(kept[0].corroborated).toBe(false);
  });

  it('still folds a repeat from the same tool', () => {
    const { collapsed } = dedupeReads([
      { source: 'handbook', text: 'the limit is 500' },
      { source: 'handbook', text: 'the limit is 500' },
    ]);
    expect(collapsed).toBe(1);
  });

  it('sees past the agent\'s own boundary markers', () => {
    // One tool's output arrives fenced and another's does not; the
    // markers are plumbing, not a difference in what was read.
    const { collapsed } = dedupeReads([
      { source: 'handbook', text: '<<<external-content>>>the limit is 500<<<external-content>>>' },
      { source: 'policy', text: 'the limit is 500' },
    ]);
    expect(collapsed).toBe(1);
  });

  it('keeps the text as it arrived for whoever reads it', () => {
    const { kept } = dedupeReads([
      { source: 'handbook', text: '<<<external-content>>>the limit is 500<<<external-content>>>' },
      { source: 'policy', text: 'the limit is 500' },
    ]);
    expect(kept[0].text).toContain('<<<external-content>>>');
  });

  it('hands back the result it kept, so its description survives folding', () => {
    const { originals } = dedupeReads([
      { source: 'handbook', text: 'the limit is 500', shape: { kind: 'text', rows: 0, columns: [], language: '', needsPaging: false, needsCollapsing: false } },
      { source: 'policy', text: 'the limit is 500' },
    ]);
    expect(originals[0].shape?.kind).toBe('text');
  });

  it('handles reading nothing', () => {
    expect(dedupeReads([])).toEqual({ kept: [], collapsed: 0, originals: [] });
  });
});

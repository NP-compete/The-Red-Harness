import { describe, expect, it } from 'vitest';

import { presentSources } from '@/lib/sources';

const used = { document: 'runbook.md', snippet: 'fail over the reader', score: 0.9 };
const unused = { document: 'old-notes.md', snippet: 'unrelated', score: 0.4 };

describe('presentSources', () => {
  it('lists what the answer used', () => {
    expect(presentSources({ used: [used], unused: [] }).cited[0].document).toBe('runbook.md');
  });

  it('numbers citations so the answer can point at them', () => {
    const shown = presentSources({ used: [used, { ...used, document: 'b.md' }], unused: [] });
    expect(shown.cited.map((c) => c.marker)).toEqual(['1', '2']);
  });

  it('keeps what was found but unused out of the citations', () => {
    const shown = presentSources({ used: [used], unused: [unused] });
    expect(shown.cited).toHaveLength(1);
    expect(shown.alsoFound[0].document).toBe('old-notes.md');
  });

  it('warns when an answer cites nothing', () => {
    const shown = presentSources({ used: [], unused: [unused] });
    expect(shown.warning).toContain('not based on');
  });

  it('does not warn when the answer is grounded', () => {
    expect(presentSources({ used: [used], unused: [] }).warning).toBeUndefined();
  });

  it('says nothing was searched when nothing was retrieved', () => {
    const shown = presentSources({ used: [], unused: [] });
    expect(shown.warning).toContain('No sources');
  });

  it('shows a snippet so a claim can be checked without opening the file', () => {
    expect(presentSources({ used: [used], unused: [] }).cited[0].snippet).toBe(
      'fail over the reader',
    );
  });

  it('shortens a long snippet rather than flooding the panel', () => {
    const long = 'x'.repeat(400);
    const shown = presentSources({ used: [{ ...used, snippet: long }], unused: [] });
    expect(shown.cited[0].snippet.length).toBeLessThanOrEqual(201);
    expect(shown.cited[0].snippet.endsWith('…')).toBe(true);
  });

  it('counts what it displays, not what it was handed', () => {
    const shown = presentSources({
      used: [used],
      unused: [unused, { ...unused, document: 'other.md' }],
    });
    expect(shown.counts).toEqual({ cited: 1, alsoFound: 2 });
  });

  it('collapses repeats of the same document in what was also found', () => {
    const shown = presentSources({ used: [], unused: [unused, unused] });
    expect(shown.alsoFound).toHaveLength(1);
  });
});

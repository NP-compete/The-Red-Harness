import { describe, expect, it } from 'vitest';

import { presentSearch } from '@/lib/search-view';

const results = [
  { id: 't1', title: 'Quarterly incident review', when: '2026-10-27', sharedByOther: false },
  { id: 't4', title: 'Shared incident notes', when: '2026-10-20', sharedByOther: true },
];

describe('presentSearch', () => {
  it('shows what was found', () => {
    expect(presentSearch('incident', results).rows).toHaveLength(2);
  });

  it('marks the part of the title that matched', () => {
    expect(presentSearch('incident', results).rows[0].highlight).toEqual([
      'Quarterly ',
      'incident',
      ' review',
    ]);
  });

  it('matches case-insensitively when highlighting', () => {
    expect(presentSearch('INCIDENT', results).rows[0].highlight[1]).toBe('incident');
  });

  it('leaves a title alone when nothing matches inside it', () => {
    const odd = [{ ...results[0], title: 'No match here' }];
    expect(presentSearch('incident', odd).rows[0].highlight).toEqual(['No match here']);
  });

  it('says when a conversation belongs to somebody else', () => {
    expect(presentSearch('incident', results).rows[1].note).toContain('Shared with you');
  });

  it('says nothing extra about your own conversation', () => {
    expect(presentSearch('incident', results).rows[0].note).toBe('');
  });

  it('counts what was found', () => {
    expect(presentSearch('incident', results).summary).toBe('2 conversations');
  });

  it('uses the singular for one result', () => {
    expect(presentSearch('incident', [results[0]]).summary).toBe('1 conversation');
  });

  it('says plainly when nothing was found', () => {
    expect(presentSearch('zzzz', []).summary).toBe('Nothing found for “zzzz”');
  });

  it('prompts rather than reporting nothing for an empty query', () => {
    const shown = presentSearch('   ', []);
    expect(shown.summary).toContain('Type to search');
    expect(shown.rows).toEqual([]);
  });
});

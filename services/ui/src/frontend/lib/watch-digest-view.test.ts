import { describe, expect, it } from 'vitest';

import { presentWatchDigest } from '@/lib/watch-digest-view';

const items = [
  { document: 'handbook', summary: 'handbook changed in expenses', deleted: false },
  { document: 'policy', summary: 'policy was deleted', deleted: true },
];

describe('presentWatchDigest', () => {
  it('says nothing when nothing you follow has changed', () => {
    expect(presentWatchDigest([])).toBeNull();
  });

  it('says how many things changed', () => {
    expect(presentWatchDigest(items)?.headline).toBe('2 sources you follow changed');
  });

  it('counts one change in the singular', () => {
    expect(presentWatchDigest([items[0]])?.headline).toBe('1 source you follow changed');
  });

  it('lists what changed', () => {
    expect(presentWatchDigest(items)?.lines).toEqual([
      'policy was deleted',
      'handbook changed in expenses',
    ]);
  });

  it('puts deletions first, since they cannot be undone by reading', () => {
    expect(presentWatchDigest(items)?.lines[0]).toBe('policy was deleted');
  });

  it('offers to stop following something', () => {
    expect(presentWatchDigest(items)?.actions).toEqual(['Stop following']);
  });

  it('treats a deletion as worth noticing', () => {
    expect(presentWatchDigest(items)?.severity).toBe('medium');
  });

  it('treats ordinary edits as a quiet note', () => {
    expect(presentWatchDigest([items[0]])?.severity).toBe('info');
  });

  it('is a note rather than something to answer', () => {
    expect(presentWatchDigest(items)?.blocking).toBe(false);
  });
});

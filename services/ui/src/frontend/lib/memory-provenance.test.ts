import { describe, expect, it } from 'vitest';

import { provenanceOf } from './memory-provenance';

describe('what is known about where a fact came from', () => {
  it('reports the day it was saved', () => {
    const found = provenanceOf({ createdAt: '2026-10-01T09:00:00Z' });
    expect(found.known).toBe(true);
    expect(found.when).not.toBe('');
  });

  it('reports the conversation', () => {
    expect(provenanceOf({ threadId: 'thread-7' }).threadId).toBe('thread-7');
  });

  it('reports both when both are there', () => {
    const found = provenanceOf({ createdAt: '2026-10-01T09:00:00Z', threadId: 't7' });
    expect(found.when).not.toBe('');
    expect(found.threadId).toBe('t7');
  });
});

describe('what is not known', () => {
  it('says nothing for an older entry', () => {
    // Written before any of this was recorded. Inventing a
    // source is worse than admitting there is none.
    expect(provenanceOf({}).known).toBe(false);
  });

  it('treats an unreadable date as no date', () => {
    // "Invalid Date" beside a fact makes the fact look broken.
    expect(provenanceOf({ createdAt: 'last Tuesday' }).when).toBe('');
  });

  it('treats an empty conversation id as none', () => {
    expect(provenanceOf({ threadId: '   ' }).threadId).toBe('');
  });

  it('survives a shape it cannot read', () => {
    expect(provenanceOf({ threadId: null }).known).toBe(false);
    expect(provenanceOf({ createdAt: undefined }).known).toBe(false);
  });
});

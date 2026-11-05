import { afterEach, describe, expect, it, vi } from 'vitest';

import { removeDuplicateMemories } from './memory-dedupe';

function answers(status: number, body: unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: status >= 200 && status < 300,
      status,
      json: async () => body,
    }),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('removeDuplicateMemories', () => {
  it('reports what it took out and what is left', async () => {
    answers(200, { removed: 2, remaining: 3 });
    expect(await removeDuplicateMemories()).toEqual({ removed: 2, remaining: 3 });
  });

  it('reports finding nothing to remove', async () => {
    answers(200, { removed: 0, remaining: 2 });
    expect(await removeDuplicateMemories()).toEqual({ removed: 0, remaining: 2 });
  });

  it('knows nothing when the agent refuses', async () => {
    answers(403, {});
    expect(await removeDuplicateMemories()).toBeNull();
  });

  it('knows nothing when the agent cannot be reached', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
    expect(await removeDuplicateMemories()).toBeNull();
  });

  it('treats a reply with no counts as nothing known', async () => {
    answers(200, {});
    expect(await removeDuplicateMemories()).toBeNull();
  });
});

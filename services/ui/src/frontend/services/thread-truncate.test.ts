import { afterEach, describe, expect, it, vi } from 'vitest';

import { withdrawFrom } from './thread-truncate';

function answers(status: number, body: unknown = {}) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: status >= 200 && status < 300,
      status,
      json: async () => body,
    }),
  );
}

afterEach(() => vi.unstubAllGlobals());

describe('withdrawFrom', () => {
  it('reports the turns that were withdrawn', async () => {
    answers(200, { removed: 2 });
    expect(await withdrawFrom('t1', 2)).toBe(true);
  });

  it('names the point to withdraw from', async () => {
    answers(200, { removed: 1 });
    await withdrawFrom('t1', 3);
    const [, init] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit];
    expect(JSON.parse(init.body as string)).toEqual({ message_index: 3 });
  });

  it('says it failed rather than letting the edit go ahead', async () => {
    answers(409, { detail: 'cannot be withdrawn' });
    expect(await withdrawFrom('t1', 2)).toBe(false);
  });

  it('says it failed when the agent cannot be reached', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
    expect(await withdrawFrom('t1', 2)).toBe(false);
  });

  it('does not ask about a conversation with nothing to withdraw', async () => {
    const fetched = vi.fn();
    vi.stubGlobal('fetch', fetched);
    expect(await withdrawFrom('', 2)).toBe(false);
    expect(fetched).not.toHaveBeenCalled();
  });
});

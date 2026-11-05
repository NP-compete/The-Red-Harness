import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./authenticated-fetch', () => ({ authenticatedFetch: vi.fn() }));
vi.mock('../lib/app-paths', () => ({
  buildAgentApiUrl: (path: string) => `/api/proxy/agent${path}`,
}));

import { authenticatedFetch } from './authenticated-fetch';
import { getThreadTokenUsage } from './token-usage-api';

function answers(body: unknown, status = 200) {
  vi.mocked(authenticatedFetch).mockResolvedValue(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  );
}

beforeEach(() => vi.mocked(authenticatedFetch).mockReset());

describe('getThreadTokenUsage', () => {
  it('reports what a conversation has used', async () => {
    answers({ thread_id: 't1', used: 13500, input_tokens: 12300, output_tokens: 1200 });
    expect(await getThreadTokenUsage('t1')).toEqual({
      used: 13500,
      inputTokens: 12300,
      outputTokens: 1200,
      cost: null,
      currency: 'USD',
    });
  });

  it('says nothing for a conversation with no record yet', async () => {
    answers({ detail: 'not found' }, 404);
    expect(await getThreadTokenUsage('t1')).toBeNull();
  });

  it('says nothing when tracking is switched off', async () => {
    // 503 is "not configured", which is not an error worth showing.
    answers({ detail: 'unavailable' }, 503);
    expect(await getThreadTokenUsage('t1')).toBeNull();
  });

  it('says nothing when the answer cannot be read', async () => {
    // A body that claims to be JSON and is not: the same failure path
    // as an unreachable agent, exercised without a throwing mock,
    // which this runner reports as a test error even when caught.
    vi.mocked(authenticatedFetch).mockResolvedValue(
      new Response('not json at all', {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    expect(await getThreadTokenUsage('t1')).toBeNull();
  });

  it('treats missing counts as zero rather than as absent', async () => {
    answers({ thread_id: 't1', used: 10 });
    expect(await getThreadTokenUsage('t1')).toEqual({
      used: 10,
      inputTokens: 0,
      outputTokens: 0,
      cost: null,
      currency: 'USD',
    });
  });

  it('carries what the tokens cost, when a price list priced them', async () => {
    answers({ thread_id: 't1', used: 10, cost: '0.0009', currency: 'USD' });
    expect((await getThreadTokenUsage('t1'))?.cost).toBe('0.0009');
  });

  it('reports an unpriced conversation as unpriced, not as free', async () => {
    answers({ thread_id: 't1', used: 10, cost: null });
    expect((await getThreadTokenUsage('t1'))?.cost).toBeNull();
  });
});

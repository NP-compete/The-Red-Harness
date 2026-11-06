import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./authenticated-fetch', () => ({ authenticatedFetch: vi.fn() }));
vi.mock('../lib/app-paths', () => ({
  buildAgentApiUrl: (path: string) => `/api/proxy/agent${path}`,
}));

import { authenticatedFetch } from './authenticated-fetch';
import { reindexThreads } from './search-reindex';

function answers(body: unknown, status = 200) {
  vi.mocked(authenticatedFetch).mockResolvedValue(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  );
}

beforeEach(() => vi.mocked(authenticatedFetch).mockReset());

describe('reindexThreads', () => {
  it('reports how many conversations were indexed', async () => {
    answers({ indexed: 14 });
    expect(await reindexThreads()).toBe(14);
  });

  it('reports an empty account as nothing indexed, not as a failure', async () => {
    answers({ indexed: 0 });
    expect(await reindexThreads()).toBe(0);
  });

  it('asks the agent to do the work', async () => {
    answers({ indexed: 1 });
    await reindexThreads();
    const [url, options] = vi.mocked(authenticatedFetch).mock.calls[0];
    expect(String(url)).toContain('/search/reindex');
    expect((options as RequestInit).method).toBe('POST');
  });

  it('says it could not when the agent refuses', async () => {
    answers({ detail: 'nope' }, 500);
    expect(await reindexThreads()).toBeNull();
  });

  it('says it could not when the answer cannot be read', async () => {
    vi.mocked(authenticatedFetch).mockResolvedValue(
      new Response('not json', { status: 200, headers: { 'Content-Type': 'application/json' } }),
    );
    expect(await reindexThreads()).toBeNull();
  });
});

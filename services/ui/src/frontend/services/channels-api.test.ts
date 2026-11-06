import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./authenticated-fetch', () => ({ authenticatedFetch: vi.fn() }));
vi.mock('../lib/app-paths', () => ({
  buildAgentApiUrl: (path: string) => `/api/proxy/agent${path}`,
}));

import { authenticatedFetch } from './authenticated-fetch';
import { listChannels } from './channels-api';

function answers(body: unknown, status = 200) {
  vi.mocked(authenticatedFetch).mockResolvedValue(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  );
}

beforeEach(() => vi.mocked(authenticatedFetch).mockReset());

describe('listChannels', () => {
  it('lists the channels that are live', async () => {
    answers({ channels: [{ name: 'support', type: 'slack', assistant_id: 'a1' }] });
    expect(await listChannels()).toEqual([
      { name: 'support', type: 'slack', assistantId: 'a1' },
    ]);
  });

  it('reports none configured as an empty list', async () => {
    answers({ channels: [] });
    expect(await listChannels()).toEqual([]);
  });

  it('reports nothing when the agent cannot answer', async () => {
    answers({ detail: 'nope' }, 500);
    expect(await listChannels()).toEqual([]);
  });

  it('survives an answer that is not shaped as expected', async () => {
    answers({ channels: 'nope' });
    expect(await listChannels()).toEqual([]);
  });

  it('skips a channel with no name to show', async () => {
    answers({ channels: [{ type: 'slack' }, { name: 'support', type: 'slack' }] });
    expect(await listChannels()).toHaveLength(1);
  });
});

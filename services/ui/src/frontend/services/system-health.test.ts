import { afterEach, describe, expect, it, vi } from 'vitest';

import { getSystemHealth } from './system-health';

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

describe('getSystemHealth', () => {
  it('reports each part the agent depends on', async () => {
    answers(200, {
      status: 'healthy',
      database: 'connected',
      langgraph_store: 'connected',
    });
    expect(await getSystemHealth()).toEqual([
      { name: 'database', state: 'connected' },
      { name: 'langgraph store', state: 'connected' },
    ]);
  });

  it('counts anything that is not connected as degraded', async () => {
    answers(200, { status: 'degraded', database: 'error: timeout' });
    expect(await getSystemHealth()).toEqual([{ name: 'database', state: 'degraded' }]);
  });

  it('leaves out the overall verdict, which is the rows themselves', async () => {
    answers(200, { status: 'healthy', database: 'connected' });
    expect((await getSystemHealth())?.map((s) => s.name)).not.toContain('status');
  });

  it('ignores anything that is not a plain answer', async () => {
    answers(200, { status: 'healthy', database: 'connected', detail: { nested: true } });
    expect((await getSystemHealth())?.map((s) => s.name)).toEqual(['database']);
  });

  it('knows nothing when the agent cannot be reached', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
    expect(await getSystemHealth()).toBeNull();
  });

  it('knows nothing when the agent refuses', async () => {
    answers(503, {});
    expect(await getSystemHealth()).toBeNull();
  });
});

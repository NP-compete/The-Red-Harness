import { afterEach, describe, expect, it, vi } from 'vitest';

import { getWhoami } from './whoami';

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

describe('getWhoami', () => {
  it('reports who the agent thinks is asking', async () => {
    answers(200, { user_id: 'dev-user', role: 'owners', is_developer: true });
    expect(await getWhoami()).toEqual({
      userId: 'dev-user',
      role: 'owners',
      isDeveloper: true,
    });
  });

  it('treats a refusal as not knowing rather than as a denial', async () => {
    answers(403, {});
    expect(await getWhoami()).toBeNull();
  });

  it('says nothing when the agent cannot be reached', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
    expect(await getWhoami()).toBeNull();
  });

  it('says nothing when the answer has no role in it', async () => {
    answers(200, { user_id: 'dev-user' });
    expect(await getWhoami()).toBeNull();
  });
});

import { afterEach, describe, expect, it, vi } from 'vitest';

import { listExtensions } from './extensions-api';

function answers(status: number, body: unknown) {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300, status, json: async () => body,
  }));
}

const LOADED = { path: 'house.style:Redactor', required: true, loaded: true, problem: '' };
const BROKEN = { path: 'gone:Thing', required: false, loaded: false, problem: 'gone: no module' };

afterEach(() => vi.unstubAllGlobals());

describe('listExtensions', () => {
  it('reports what a deployment has interposed', async () => {
    answers(200, { extensions: [LOADED] });
    expect((await listExtensions())?.[0].path).toBe('house.style:Redactor');
  });

  it('says whether each one is in the path', async () => {
    answers(200, { extensions: [LOADED, BROKEN] });
    const found = await listExtensions();
    expect(found?.map((e) => e.loaded)).toEqual([true, false]);
  });

  it('carries why one is not', async () => {
    answers(200, { extensions: [BROKEN] });
    expect((await listExtensions())?.[0].problem).toMatch(/no module/);
  });

  it('treats a deployment with none as none, not as a failure', async () => {
    answers(200, { extensions: [] });
    expect(await listExtensions()).toEqual([]);
  });

  it('says nothing when the agent cannot be reached', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
    expect(await listExtensions()).toBeNull();
  });

  it('says nothing when the agent refuses', async () => {
    answers(403, {});
    expect(await listExtensions()).toBeNull();
  });
});

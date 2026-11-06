import { afterEach, describe, expect, it, vi } from 'vitest';

import { getExtractionStatus } from './extraction-status';

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

const PAYLOAD = {
  engine: 'builtin',
  reachable: true,
  detail: 'built-in parsers',
  fallback: true,
  handles: [],
  max_bytes: 20971520,
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('getExtractionStatus', () => {
  it('names what reads an attachment', async () => {
    answers(200, PAYLOAD);
    expect((await getExtractionStatus())?.engine).toBe('builtin');
  });

  it('says whether it can be reached at all', async () => {
    answers(200, { ...PAYLOAD, reachable: false, detail: 'connection refused' });
    const status = await getExtractionStatus();
    expect(status?.reachable).toBe(false);
    expect(status?.detail).toBe('connection refused');
  });

  it('reports the largest file that will be read', async () => {
    answers(200, PAYLOAD);
    expect((await getExtractionStatus())?.maxBytes).toBe(20971520);
  });

  it('reports the kinds it handles when it names any', async () => {
    answers(200, { ...PAYLOAD, engine: 'external', handles: ['.pdf', '.docx'] });
    expect((await getExtractionStatus())?.handles).toEqual(['.pdf', '.docx']);
  });

  it('says whether something else takes over when it cannot cope', async () => {
    answers(200, { ...PAYLOAD, fallback: false });
    expect((await getExtractionStatus())?.fallback).toBe(false);
  });

  it('knows nothing when the reader may not ask', async () => {
    answers(403, {});
    expect(await getExtractionStatus()).toBeNull();
  });

  it('knows nothing when the agent cannot be reached', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
    expect(await getExtractionStatus()).toBeNull();
  });
});

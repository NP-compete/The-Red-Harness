import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../lib/app-paths', () => ({
  buildAgentApiUrl: (path: string) => `/api/proxy/agent${path}`,
}));

import { readShared } from './shared-read';

function answers(body: unknown, status = 200) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(
      new Response(JSON.stringify(body), {
        status,
        headers: { 'Content-Type': 'application/json' },
      }),
    ),
  );
}

beforeEach(() => vi.unstubAllGlobals());

describe('readShared', () => {
  it('returns the shared conversation', async () => {
    answers({ share_id: 's1', title: 'Travel limits', captured_at: '2026-03-01T12:00:00Z', messages: [{ type: 'human', content: 'q' }], attachment_names: [] });
    const found = await readShared('s1');
    expect(found.state).toBe('ok');
  });

  it('carries the conversation title', async () => {
    answers({ share_id: 's1', title: 'Travel limits', messages: [], attachment_names: [] });
    const found = await readShared('s1');
    expect(found.state === 'ok' && found.title).toBe('Travel limits');
  });

  it('carries the messages', async () => {
    answers({ share_id: 's1', title: 't', messages: [{ type: 'ai', content: 'hello' }], attachment_names: [] });
    const found = await readShared('s1');
    expect(found.state === 'ok' && found.messages).toHaveLength(1);
  });

  it('names attachments without offering the files', async () => {
    answers({ share_id: 's1', title: 't', messages: [], attachment_names: ['handbook.pdf'] });
    const found = await readShared('s1');
    expect(found.state === 'ok' && found.attachmentNames).toEqual(['handbook.pdf']);
  });

  it('tells a revoked link apart from an expired one', async () => {
    answers({ detail: 'This link was revoked' }, 410);
    const found = await readShared('s1');
    expect(found).toEqual({ state: 'gone', reason: 'This link was revoked' });
  });

  it('reports an expired link in its own words', async () => {
    answers({ detail: 'This link has expired' }, 410);
    const found = await readShared('s1');
    expect(found.state === 'gone' && found.reason).toBe('This link has expired');
  });

  it('reports a link that never existed', async () => {
    answers({ detail: 'This link is not valid' }, 404);
    expect((await readShared('s1')).state).toBe('missing');
  });

  it('reports a link that needs signing in', async () => {
    answers({ detail: 'Not authenticated' }, 401);
    expect((await readShared('s1')).state).toBe('sign-in');
  });

  it('survives the agent being unreachable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
    expect((await readShared('s1')).state).toBe('unavailable');
  });
});

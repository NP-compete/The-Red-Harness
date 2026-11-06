import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./authenticated-fetch', () => ({ authenticatedFetch: vi.fn() }));
vi.mock('../lib/app-paths', () => ({
  buildAgentApiUrl: (path: string) => `/api/proxy/agent${path}`,
}));

import { authenticatedFetch } from './authenticated-fetch';
import { createShare, getShare, listShares, revokeShare } from './share-api';

function answers(body: unknown, status = 200) {
  vi.mocked(authenticatedFetch).mockResolvedValue(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  );
}

beforeEach(() => vi.mocked(authenticatedFetch).mockReset());

describe('share-api', () => {
  it('reports a conversation that is not shared', async () => {
    answers({ shared: false });
    expect(await getShare('t1')).toBeNull();
  });

  it('reports an existing share', async () => {
    answers({ shared: true, share_id: 's1', scope: 'authenticated', active: true, views: 3, expires_at: '2026-03-08T12:00:00Z', path: '/shared/s1' });
    expect((await getShare('t1'))?.shareId).toBe('s1');
  });

  it('carries how often the link was opened', async () => {
    answers({ shared: true, share_id: 's1', scope: 'authenticated', active: true, views: 3, expires_at: null, path: '/shared/s1' });
    expect((await getShare('t1'))?.views).toBe(3);
  });

  it('says nothing rather than guessing when the agent cannot answer', async () => {
    answers({ detail: 'nope' }, 500);
    expect(await getShare('t1')).toBeNull();
  });

  it('creates a link', async () => {
    answers({ share_id: 's2', scope: 'authenticated', active: true, views: 0, expires_at: null, path: '/shared/s2' });
    expect((await createShare('t1', 'authenticated', 7))?.shareId).toBe('s2');
  });

  it('asks for the scope and lifetime it was given', async () => {
    answers({ share_id: 's2', scope: 'public', active: true, views: 0, expires_at: null, path: '/shared/s2' });
    await createShare('t1', 'public', 3);
    const [, options] = vi.mocked(authenticatedFetch).mock.calls[0];
    expect(JSON.parse(String((options as RequestInit).body))).toEqual({
      scope: 'public',
      expiry_days: 3,
    });
  });

  it('revokes a link', async () => {
    answers({ revoked: true });
    expect(await revokeShare('t1')).toBe(true);
  });

  it('reports a revoke that did not happen', async () => {
    answers({ revoked: false });
    expect(await revokeShare('t1')).toBe(false);
  });
});

describe('listShares', () => {
  it('lists everything this account has published', async () => {
    answers({
      shares: [
        { share_id: 's1', thread_id: 't1', title: 'Travel limits', scope: 'authenticated', active: true, views: 2, expires_at: null, path: '/shared/s1' },
        { share_id: 's2', thread_id: 't2', title: 'Expenses', scope: 'public', active: false, views: 0, expires_at: null, path: '/shared/s2' },
      ],
    });
    expect(await listShares()).toHaveLength(2);
  });

  it('carries which conversation each link belongs to', async () => {
    answers({ shares: [{ share_id: 's1', thread_id: 't1', title: 'Travel limits', scope: 'authenticated', active: true, views: 2, expires_at: null, path: '/shared/s1' }] });
    const [share] = await listShares();
    expect(share.threadId).toBe('t1');
  });

  it('carries the conversation title, so a link is recognisable', async () => {
    answers({ shares: [{ share_id: 's1', thread_id: 't1', title: 'Travel limits', scope: 'authenticated', active: true, views: 2, expires_at: null, path: '/shared/s1' }] });
    const [share] = await listShares();
    expect(share.title).toBe('Travel limits');
  });

  it('reports nothing shared as nothing, not as a failure', async () => {
    answers({ shares: [] });
    expect(await listShares()).toEqual([]);
  });

  it('reports nothing when the agent cannot answer', async () => {
    answers({ detail: 'nope' }, 500);
    expect(await listShares()).toEqual([]);
  });
});

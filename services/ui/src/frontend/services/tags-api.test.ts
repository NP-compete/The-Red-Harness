import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./authenticated-fetch', () => ({ authenticatedFetch: vi.fn() }));
vi.mock('../lib/app-paths', () => ({
  buildAgentApiUrl: (path: string) => `/api/proxy/agent${path}`,
}));

import { authenticatedFetch } from './authenticated-fetch';
import { getThreadTags, listTags, setThreadTags, threadsWithTag } from './tags-api';

function answers(body: unknown, status = 200) {
  vi.mocked(authenticatedFetch).mockResolvedValue(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  );
}

beforeEach(() => vi.mocked(authenticatedFetch).mockReset());

describe('tags-api', () => {
  it('reads the tags on a conversation', async () => {
    answers({ tags: ['billing', 'travel'] });
    expect(await getThreadTags('t1')).toEqual(['billing', 'travel']);
  });

  it('reports no tags rather than failing', async () => {
    answers({ detail: 'nope' }, 500);
    expect(await getThreadTags('t1')).toEqual([]);
  });

  it('replaces the whole set, as the agent expects', async () => {
    answers({ tags: ['billing'] });
    await setThreadTags('t1', ['billing']);
    const [url, options] = vi.mocked(authenticatedFetch).mock.calls[0];
    expect(String(url)).toContain('/threads/t1/tags');
    expect((options as RequestInit).method).toBe('PUT');
    expect(JSON.parse(String((options as RequestInit).body))).toEqual({ tags: ['billing'] });
  });

  it('hands back what the agent settled on, not what was sent', async () => {
    // The agent lowercases, trims and sorts; echoing the input would
    // show a tag that is not the one stored.
    answers({ tags: ['billing', 'travel'] });
    expect(await setThreadTags('t1', ['Travel', ' billing '])).toEqual(['billing', 'travel']);
  });

  it('reports a rejected tag as a refusal, not a silent success', async () => {
    answers({ detail: 'a tag cannot be empty' }, 422);
    expect(await setThreadTags('t1', [''])).toBeNull();
  });

  it('lists every tag with its count', async () => {
    answers({ tags: [{ tag: 'billing', threads: 4 }, { tag: 'travel', threads: 1 }] });
    expect(await listTags()).toEqual([
      { tag: 'billing', threads: 4 },
      { tag: 'travel', threads: 1 },
    ]);
  });

  it('reports no tags at all as an empty list', async () => {
    answers({ tags: [] });
    expect(await listTags()).toEqual([]);
  });
});

describe('threadsWithTag', () => {
  it('finds the conversations carrying a tag', async () => {
    answers({
      tag: 'billing',
      threads: [
        { thread_id: 't1', title: 'Invoices', tags: ['billing'], updated_at: '2026-03-01T12:00:00Z' },
      ],
    });
    const found = await threadsWithTag('billing');
    expect(found.map((t) => t.id)).toEqual(['t1']);
  });

  it('carries each conversation title', async () => {
    answers({ tag: 'billing', threads: [{ thread_id: 't1', title: 'Invoices', tags: ['billing'], updated_at: null }] });
    expect((await threadsWithTag('billing'))[0].title).toBe('Invoices');
  });

  it('carries the other tags each one has', async () => {
    answers({ tag: 'billing', threads: [{ thread_id: 't1', title: 'Invoices', tags: ['billing', 'travel'], updated_at: null }] });
    expect((await threadsWithTag('billing'))[0].tags).toEqual(['billing', 'travel']);
  });

  it('reports a tag nobody used as no conversations', async () => {
    answers({ tag: 'nope', threads: [] });
    expect(await threadsWithTag('nope')).toEqual([]);
  });

  it('asks for the tag as given', async () => {
    answers({ tag: 'billing', threads: [] });
    await threadsWithTag('billing');
    expect(String(vi.mocked(authenticatedFetch).mock.calls[0][0])).toContain('/tags/billing/threads');
  });

  it('escapes a tag with a space in it', async () => {
    answers({ tag: 'to read', threads: [] });
    await threadsWithTag('to read');
    expect(String(vi.mocked(authenticatedFetch).mock.calls[0][0])).toContain('to%20read');
  });

  it('reports nothing when the agent cannot answer', async () => {
    answers({ detail: 'nope' }, 500);
    expect(await threadsWithTag('billing')).toEqual([]);
  });
});

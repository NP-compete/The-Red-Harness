import { afterEach, describe, expect, it, vi } from 'vitest';

import { editInLibrary } from './knowledge-api';

/**
 * Saving a change to a note.
 *
 * The interesting half is the refusal. The agent knows how
 * much room is left and whose note it is; a generic "could
 * not save" here sends somebody guessing at which of those
 * went wrong.
 */

afterEach(() => vi.restoreAllMocks());

const answer = (status: number, body: unknown = {}) =>
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  );

describe('saving a change', () => {
  it('reports success', async () => {
    answer(200, { status: 'saved' });
    expect(await editInLibrary('user:1', 'A note', 'new text')).toEqual({ ok: true });
  });

  it('sends the change to that note', async () => {
    const fetched = answer(200, {});
    await editInLibrary('user:1', 'A note', 'new text');
    const [url, init] = fetched.mock.calls[0] as [string, RequestInit];
    expect(url).toContain('user%3A1');
    expect(init.method).toBe('PUT');
    expect(JSON.parse(String(init.body))).toEqual({ title: 'A note', text: 'new text' });
  });
});

describe('when it is refused', () => {
  it('passes on what the agent said', async () => {
    // It knows the numbers: "4 of 10 bytes used" is actionable
    // and "could not save" is not.
    answer(413, { detail: 'storing 90 more bytes would put you over your limit' });
    const found = await editInLibrary('user:1', 't', 'x');
    expect(found).toEqual({
      ok: false,
      detail: 'storing 90 more bytes would put you over your limit',
    });
  });

  it('says something when the agent says nothing', async () => {
    answer(500, {});
    const found = await editInLibrary('user:1', 't', 'x');
    expect(found.ok).toBe(false);
    expect((found as { detail: string }).detail).toBeTruthy();
  });

  it('says so when the agent cannot be reached', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('offline'));
    const found = await editInLibrary('user:1', 't', 'x');
    expect(found.ok).toBe(false);
  });
});

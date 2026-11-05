import { renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  forgetReasoningProfiles,
  useReasoningProfiles,
} from '../useReasoningProfiles';

/**
 * Asked once, and the answer kept.
 *
 * The fault this guards against showed up only in a browser:
 * the hook that starts a run is created at the moment the first
 * message is sent, so its own fetch was still in flight when
 * that message went out. The conversation's chosen profile was
 * dropped on its first turn and worked on every turn after —
 * which nobody reports, because by the time you notice, it
 * works.
 */

const answer = (profiles: unknown) =>
  Promise.resolve(
    new Response(JSON.stringify({ profiles }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }),
  );

beforeEach(() => {
  forgetReasoningProfiles();
  vi.stubGlobal('fetch', vi.fn(() => answer([{ name: 'fast', effort: 'low' }])));
});

afterEach(() => {
  vi.restoreAllMocks();
  forgetReasoningProfiles();
});

describe('asking the agent', () => {
  it('returns what it offers', async () => {
    const { result } = renderHook(() => useReasoningProfiles());
    await waitFor(() => expect(result.current).toHaveLength(1));
    expect(result.current[0].name).toBe('fast');
  });

  it('asks once however many components want it', async () => {
    const first = renderHook(() => useReasoningProfiles());
    const second = renderHook(() => useReasoningProfiles());
    await waitFor(() => expect(first.result.current).toHaveLength(1));
    await waitFor(() => expect(second.result.current).toHaveLength(1));
    expect(vi.mocked(fetch)).toHaveBeenCalledTimes(1);
  });

  it('gives a later component the answer straight away', async () => {
    // The one that mattered. A component created after the
    // answer arrived must not start empty and catch up a tick
    // later — by then it has already sent the message.
    const early = renderHook(() => useReasoningProfiles());
    await waitFor(() => expect(early.result.current).toHaveLength(1));

    const late = renderHook(() => useReasoningProfiles());
    expect(late.result.current).toHaveLength(1);
  });

  it('offers nothing when the agent says nothing', async () => {
    vi.mocked(fetch).mockImplementation(() => answer([]));
    const { result } = renderHook(() => useReasoningProfiles());
    await waitFor(() => expect(result.current).toEqual([]));
  });

  it('offers nothing when the agent cannot be asked', async () => {
    vi.mocked(fetch).mockImplementation(() => Promise.reject(new Error('down')));
    const { result } = renderHook(() => useReasoningProfiles());
    await waitFor(() => expect(result.current).toEqual([]));
  });

  it('offers nothing when the answer is the wrong shape', async () => {
    vi.mocked(fetch).mockImplementation(() => answer('not a list'));
    const { result } = renderHook(() => useReasoningProfiles());
    await waitFor(() => expect(result.current).toEqual([]));
  });
});

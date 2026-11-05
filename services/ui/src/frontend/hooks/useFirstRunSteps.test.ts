import { renderHook, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { useFirstRunSteps } from './useFirstRunSteps';

const api = vi.hoisted(() => ({ listDocuments: vi.fn() }));
vi.mock('../services/documents-api', () => api);

function documents(count: number) {
  api.listDocuments.mockResolvedValue({
    documents: Array.from({ length: count }, (_, i) => ({ path: `d${i}.md` })),
  });
}

afterEach(() => vi.clearAllMocks());

describe('useFirstRunSteps', () => {
  it('offers nothing before it knows anything', () => {
    documents(0);
    const { result } = renderHook(() => useFirstRunSteps({ chats: 0 }));
    expect(result.current).toEqual([]);
  });

  it('asks an empty workspace to connect a source', async () => {
    documents(0);
    const { result } = renderHook(() => useFirstRunSteps({ chats: 0 }));
    await waitFor(() => expect(result.current).toContain('connect_source'));
  });

  it('asks an empty workspace for its first question', async () => {
    documents(0);
    const { result } = renderHook(() => useFirstRunSteps({ chats: 0 }));
    await waitFor(() => expect(result.current).toContain('ask_something'));
  });

  it('stops asking for a source once there is one', async () => {
    documents(2);
    const { result } = renderHook(() => useFirstRunSteps({ chats: 0 }));
    await waitFor(() => expect(result.current.length).toBeGreaterThan(0));
    expect(result.current).not.toContain('connect_source');
  });

  it('stops asking for a first question once one was asked', async () => {
    documents(0);
    const { result } = renderHook(() => useFirstRunSteps({ chats: 3 }));
    await waitFor(() => expect(result.current.length).toBeGreaterThan(0));
    expect(result.current).not.toContain('ask_something');
  });

  it('offers nothing to a workspace that is under way', async () => {
    documents(2);
    const { result } = renderHook(() => useFirstRunSteps({ chats: 3 }));
    await waitFor(() => expect(api.listDocuments).toHaveBeenCalled());
    expect(result.current).toEqual([]);
  });

  it('puts connecting a source before asking, which needs it', async () => {
    documents(0);
    const { result } = renderHook(() => useFirstRunSteps({ chats: 0 }));
    await waitFor(() => expect(result.current).toHaveLength(2));
    expect(result.current).toEqual(['connect_source', 'ask_something']);
  });

  it('never invites a team it cannot see', async () => {
    // There is no team data here, so offering it would be a card
    // that leads nowhere.
    documents(0);
    const { result } = renderHook(() => useFirstRunSteps({ chats: 0 }));
    await waitFor(() => expect(result.current.length).toBeGreaterThan(0));
    expect(result.current).not.toContain('invite_others');
  });

  it('says nothing when the documents cannot be counted', async () => {
    // Guessing "no documents" would greet an established workspace
    // with a first-run card every time the call failed.
    api.listDocuments.mockRejectedValue(new Error('unreachable'));
    const { result } = renderHook(() => useFirstRunSteps({ chats: 0 }));
    await waitFor(() => expect(api.listDocuments).toHaveBeenCalled());
    expect(result.current).toEqual([]);
  });
});

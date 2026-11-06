import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useCommands } from './useCommands';

const answer = vi.hoisted(() => ({ ok: true, body: {} as unknown }));

beforeEach(() => {
  answer.ok = true;
  answer.body = { commands: [{ name: 'summarise', help: 'Sum up this conversation' }] };
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation(() =>
      Promise.resolve({ ok: answer.ok, json: () => Promise.resolve(answer.body) }),
    ),
  );
});

describe('useCommands', () => {
  it('offers what the agent lists', async () => {
    const { result } = renderHook(() => useCommands());
    await waitFor(() => expect(result.current).toHaveLength(1));
    expect(result.current[0].name).toBe('summarise');
  });

  it('offers nothing before the agent has answered', () => {
    const { result } = renderHook(() => useCommands());
    expect(result.current).toEqual([]);
  });

  it('offers nothing when the agent cannot be asked', async () => {
    answer.ok = false;
    const { result } = renderHook(() => useCommands());
    await waitFor(() => expect(fetch).toHaveBeenCalled());
    expect(result.current).toEqual([]);
  });

  it('survives an answer that is not shaped as expected', async () => {
    answer.body = { commands: 'nope' };
    const { result } = renderHook(() => useCommands());
    await waitFor(() => expect(fetch).toHaveBeenCalled());
    expect(result.current).toEqual([]);
  });
});

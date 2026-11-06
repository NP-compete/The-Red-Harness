import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useStoppingRun } from './useStoppingRun';

const stillGoing = vi.hoisted(() => vi.fn());

vi.mock('../services/run-status', () => ({
  runStillGoing: stillGoing,
}));

beforeEach(() => {
  vi.useFakeTimers();
  stillGoing.mockResolvedValue(true);
});

afterEach(() => {
  vi.useRealTimers();
  stillGoing.mockReset();
});

/** Let the polling promise settle between timer steps. */
async function advance(ms: number) {
  await act(async () => {
    vi.advanceTimersByTime(ms);
    await Promise.resolve();
    await Promise.resolve();
  });
}

describe('useStoppingRun', () => {
  it('says nothing until a stop is asked for', () => {
    const { result } = renderHook(() => useStoppingRun('t1'));
    expect(result.current.stopping).toBe(false);
  });

  it('holds the stopping state the moment a stop is asked for', () => {
    const { result } = renderHook(() => useStoppingRun('t1'));
    act(() => result.current.stopRequested());
    expect(result.current.stopping).toBe(true);
  });

  it('keeps holding it while the agent is still working', async () => {
    const { result } = renderHook(() => useStoppingRun('t1'));
    act(() => result.current.stopRequested());
    await advance(6000);
    expect(result.current.stopping).toBe(true);
  });

  it('lets go once the agent has actually stopped', async () => {
    const { result } = renderHook(() => useStoppingRun('t1'));
    act(() => result.current.stopRequested());
    stillGoing.mockResolvedValue(false);
    await advance(2500);
    expect(result.current.stopping).toBe(false);
  });

  it('gives up rather than claiming to be stopping for ever', async () => {
    const { result } = renderHook(() => useStoppingRun('t1'));
    act(() => result.current.stopRequested());
    await advance(45000);
    expect(result.current.stopping).toBe(false);
  });

  it('stops asking once it has let go', async () => {
    const { result } = renderHook(() => useStoppingRun('t1'));
    act(() => result.current.stopRequested());
    stillGoing.mockResolvedValue(false);
    await advance(2500);
    const asked = stillGoing.mock.calls.length;
    await advance(10000);
    expect(stillGoing.mock.calls.length).toBe(asked);
  });

  it('asks about the conversation the stop was for', async () => {
    const { result } = renderHook(() => useStoppingRun('t7'));
    act(() => result.current.stopRequested());
    await advance(2500);
    expect(stillGoing).toHaveBeenCalledWith('t7');
  });

  it('does not poll a conversation that has no id yet', async () => {
    const { result } = renderHook(() => useStoppingRun(undefined));
    act(() => result.current.stopRequested());
    await advance(5000);
    expect(stillGoing).not.toHaveBeenCalled();
  });

  it('lets go when moving to another conversation', async () => {
    const { result, rerender } = renderHook(({ id }) => useStoppingRun(id), {
      initialProps: { id: 't1' },
    });
    act(() => result.current.stopRequested());
    rerender({ id: 't2' });
    expect(result.current.stopping).toBe(false);
  });

  it('can be asked a second time after it let go', async () => {
    const { result } = renderHook(() => useStoppingRun('t1'));
    act(() => result.current.stopRequested());
    stillGoing.mockResolvedValue(false);
    await advance(2500);
    stillGoing.mockResolvedValue(true);
    act(() => result.current.stopRequested());
    expect(result.current.stopping).toBe(true);
  });
});

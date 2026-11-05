import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useQuietFor } from './useQuietFor';

describe('useQuietFor', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('counts nothing while nothing is running', () => {
    const { result } = renderHook(() => useQuietFor(false, 'a'));
    act(() => vi.advanceTimersByTime(5000));
    expect(result.current).toBe(0);
  });

  it('counts the silence while something is running', () => {
    const { result } = renderHook(() => useQuietFor(true, 'a'));
    act(() => vi.advanceTimersByTime(3000));
    expect(result.current).toBe(3);
  });

  it('starts again whenever something arrives', () => {
    const { result, rerender } = renderHook(({ sig }) => useQuietFor(true, sig), {
      initialProps: { sig: 'a' },
    });
    act(() => vi.advanceTimersByTime(3000));
    rerender({ sig: 'b' });
    expect(result.current).toBe(0);
  });

  it('counts again from the new arrival', () => {
    const { result, rerender } = renderHook(({ sig }) => useQuietFor(true, sig), {
      initialProps: { sig: 'a' },
    });
    act(() => vi.advanceTimersByTime(3000));
    rerender({ sig: 'b' });
    act(() => vi.advanceTimersByTime(2000));
    expect(result.current).toBe(2);
  });

  it('forgets the count once the run ends', () => {
    const { result, rerender } = renderHook(({ on }) => useQuietFor(on, 'a'), {
      initialProps: { on: true },
    });
    act(() => vi.advanceTimersByTime(3000));
    rerender({ on: false });
    expect(result.current).toBe(0);
  });

  it('stops its timer when it goes away', () => {
    const { unmount } = renderHook(() => useQuietFor(true, 'a'));
    act(() => vi.advanceTimersByTime(1000));
    unmount();
    expect(() => vi.advanceTimersByTime(5000)).not.toThrow();
  });
});

import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useConnectionState } from './useConnectionState';

function setOnline(value: boolean) {
  Object.defineProperty(window.navigator, 'onLine', { value, configurable: true });
  window.dispatchEvent(new Event(value ? 'online' : 'offline'));
}

describe('useConnectionState', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    Object.defineProperty(window.navigator, 'onLine', { value: true, configurable: true });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('starts from whatever the browser reports', () => {
    const { result } = renderHook(() => useConnectionState());
    expect(result.current.connected).toBe(true);
  });

  it('notices the connection going away', () => {
    const { result } = renderHook(() => useConnectionState());
    act(() => setOnline(false));
    expect(result.current.connected).toBe(false);
  });

  it('notices the connection coming back', () => {
    const { result } = renderHook(() => useConnectionState());
    act(() => setOnline(false));
    act(() => setOnline(true));
    expect(result.current.connected).toBe(true);
  });

  it('counts how long the connection has been gone', () => {
    const { result } = renderHook(() => useConnectionState());
    act(() => setOnline(false));
    act(() => vi.advanceTimersByTime(3000));
    expect(result.current.secondsDown).toBe(3);
  });

  it('stops counting once the connection returns', () => {
    const { result } = renderHook(() => useConnectionState());
    act(() => setOnline(false));
    act(() => vi.advanceTimersByTime(3000));
    act(() => setOnline(true));
    expect(result.current.secondsDown).toBe(0);
  });

  it('says nothing is worth warning about during a blip', () => {
    const { result } = renderHook(() => useConnectionState());
    act(() => setOnline(false));
    act(() => vi.advanceTimersByTime(2000));
    expect(result.current.warn).toBe(false);
  });

  it('warns once an outage has lasted', () => {
    const { result } = renderHook(() => useConnectionState());
    act(() => setOnline(false));
    act(() => vi.advanceTimersByTime(10000));
    expect(result.current.warn).toBe(true);
  });

  it('never warns while connected', () => {
    const { result } = renderHook(() => useConnectionState());
    act(() => vi.advanceTimersByTime(60000));
    expect(result.current.warn).toBe(false);
  });

  it('stops its timer when it goes away', () => {
    const { unmount } = renderHook(() => useConnectionState());
    act(() => setOnline(false));
    unmount();
    expect(() => vi.advanceTimersByTime(5000)).not.toThrow();
  });
});

import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useAnnouncer } from './useAnnouncer';

describe('useAnnouncer', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('says nothing before anything has happened', () => {
    const { result } = renderHook(() =>
      useAnnouncer({ streaming: false, answerLength: 0, needsApproval: false, failed: false }),
    );
    expect(result.current.message).toBe('');
  });

  it('reports progress once enough has been written', () => {
    const { result, rerender } = renderHook((props) => useAnnouncer(props), {
      initialProps: { streaming: true, answerLength: 0, needsApproval: false, failed: false },
    });
    act(() => vi.advanceTimersByTime(4000));
    rerender({ streaming: true, answerLength: 250, needsApproval: false, failed: false });
    expect(result.current.message).toBe('Still writing');
  });

  it('stays quiet while only a few characters have arrived', () => {
    const { result, rerender } = renderHook((props) => useAnnouncer(props), {
      initialProps: { streaming: true, answerLength: 0, needsApproval: false, failed: false },
    });
    act(() => vi.advanceTimersByTime(4000));
    rerender({ streaming: true, answerLength: 20, needsApproval: false, failed: false });
    expect(result.current.message).toBe('');
  });

  it('stays quiet when a lot arrives in quick succession', () => {
    const { result, rerender } = renderHook((props) => useAnnouncer(props), {
      initialProps: { streaming: true, answerLength: 0, needsApproval: false, failed: false },
    });
    rerender({ streaming: true, answerLength: 250, needsApproval: false, failed: false });
    expect(result.current.message).toBe('');
  });

  it('interrupts when something needs a person', () => {
    const { result } = renderHook(() =>
      useAnnouncer({ streaming: true, answerLength: 10, needsApproval: true, failed: false }),
    );
    expect(result.current.message).toBe('Waiting for your approval');
  });

  it('interrupts assertively for approval', () => {
    const { result } = renderHook(() =>
      useAnnouncer({ streaming: true, answerLength: 10, needsApproval: true, failed: false }),
    );
    expect(result.current.assertive).toBe(true);
  });

  it('interrupts when the run failed', () => {
    const { result } = renderHook(() =>
      useAnnouncer({ streaming: false, answerLength: 0, needsApproval: false, failed: true }),
    );
    expect(result.current.message).toBe('Something went wrong');
  });

  it('does not interrupt for ordinary progress', () => {
    const { result, rerender } = renderHook((props) => useAnnouncer(props), {
      initialProps: { streaming: true, answerLength: 0, needsApproval: false, failed: false },
    });
    act(() => vi.advanceTimersByTime(4000));
    rerender({ streaming: true, answerLength: 250, needsApproval: false, failed: false });
    expect(result.current.assertive).toBe(false);
  });

  it('does not repeat itself', () => {
    const { result, rerender } = renderHook((props) => useAnnouncer(props), {
      initialProps: { streaming: true, answerLength: 10, needsApproval: true, failed: false },
    });
    expect(result.current.message).toBe('Waiting for your approval');
    act(() => vi.advanceTimersByTime(5000));
    rerender({ streaming: true, answerLength: 300, needsApproval: true, failed: false });
    expect(result.current.message).toBe('Waiting for your approval');
  });
});

describe('after a failure is over', () => {
  const failing = {
    streaming: false,
    answerLength: 0,
    needsApproval: false,
    failed: true,
  };

  it('says so while it is failing', () => {
    const { result } = renderHook((r) => useAnnouncer(r), { initialProps: failing });
    expect(result.current.message).toBe('Something went wrong');
  });

  it('stops saying so once the run has recovered', () => {
    // The region keeps its last line so a reader does not hear the
    // same thing twice. A failure that is no longer true is the one
    // line that must not be kept: a retry succeeds and assistive
    // technology is still holding "Something went wrong".
    const { result, rerender } = renderHook((r) => useAnnouncer(r), {
      initialProps: failing,
    });
    rerender({ ...failing, failed: false, answerLength: 20 });
    expect(result.current.message).not.toBe('Something went wrong');
  });

  it('keeps an ordinary line in place, which is harmless', () => {
    const { result, rerender } = renderHook((r) => useAnnouncer(r), {
      initialProps: { streaming: true, answerLength: 0, needsApproval: false, failed: false },
    });
    rerender({ streaming: true, answerLength: 400, needsApproval: false, failed: false });
    const said = result.current.message;
    rerender({ streaming: true, answerLength: 401, needsApproval: false, failed: false });
    expect(result.current.message).toBe(said);
  });

  it('says so again if it fails a second time', () => {
    const { result, rerender } = renderHook((r) => useAnnouncer(r), {
      initialProps: failing,
    });
    rerender({ ...failing, failed: false });
    rerender({ ...failing, failed: true });
    expect(result.current.message).toBe('Something went wrong');
  });
});

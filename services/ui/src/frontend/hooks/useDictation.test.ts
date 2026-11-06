import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useDictation } from './useDictation';

const api = vi.hoisted(() => ({
  dictationOffered: vi.fn(),
  transcribeDictation: vi.fn(),
}));
vi.mock('../services/speech-api', () => api);

class FakeRecorder {
  static last: FakeRecorder | null = null;
  ondataavailable: ((event: { data: Blob }) => void) | null = null;
  onstop: (() => void) | null = null;
  state = 'inactive';

  constructor(public stream: unknown) {
    FakeRecorder.last = this;
  }

  start() {
    this.state = 'recording';
  }

  stop() {
    this.state = 'inactive';
    this.ondataavailable?.({ data: new Blob(['audio'], { type: 'audio/webm' }) });
    this.onstop?.();
  }
}

const stopTrack = vi.fn();

beforeEach(() => {
  api.dictationOffered.mockResolvedValue(true);
  api.transcribeDictation.mockResolvedValue({ text: 'book the room' });
  FakeRecorder.last = null;
  stopTrack.mockClear();
  vi.stubGlobal('MediaRecorder', FakeRecorder);
  vi.stubGlobal('navigator', {
    mediaDevices: {
      getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop: stopTrack }] }),
    },
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe('useDictation', () => {
  it('is not offered until the agent says it can do the work', async () => {
    api.dictationOffered.mockResolvedValue(false);
    const { result } = renderHook(() => useDictation());
    await waitFor(() => expect(api.dictationOffered).toHaveBeenCalled());
    expect(result.current.offered).toBe(false);
  });

  it('is offered when the agent says it can', async () => {
    const { result } = renderHook(() => useDictation());
    await waitFor(() => expect(result.current.offered).toBe(true));
  });

  it('is not recording to begin with', async () => {
    const { result } = renderHook(() => useDictation());
    await waitFor(() => expect(result.current.offered).toBe(true));
    expect(result.current.recording).toBe(false);
  });

  it('records when asked to', async () => {
    const { result } = renderHook(() => useDictation());
    await waitFor(() => expect(result.current.offered).toBe(true));
    await act(async () => {
      await result.current.start();
    });
    expect(result.current.recording).toBe(true);
  });

  it('hands back what was said, for the person to read first', async () => {
    const said: string[] = [];
    const { result } = renderHook(() => useDictation((text) => said.push(text)));
    await waitFor(() => expect(result.current.offered).toBe(true));
    await act(async () => {
      await result.current.start();
    });
    await act(async () => {
      result.current.stop();
    });
    await waitFor(() => expect(said).toEqual(['book the room']));
  });

  it('releases the microphone when it stops', async () => {
    const { result } = renderHook(() => useDictation());
    await waitFor(() => expect(result.current.offered).toBe(true));
    await act(async () => {
      await result.current.start();
    });
    await act(async () => {
      result.current.stop();
    });
    await waitFor(() => expect(stopTrack).toHaveBeenCalled());
  });

  it('says why nothing arrived when the recording could not be used', async () => {
    api.transcribeDictation.mockResolvedValue({ text: '', problem: 'Too long.' });
    const { result } = renderHook(() => useDictation());
    await waitFor(() => expect(result.current.offered).toBe(true));
    await act(async () => {
      await result.current.start();
    });
    await act(async () => {
      result.current.stop();
    });
    await waitFor(() => expect(result.current.problem).toBe('Too long.'));
  });

  it('does not report silence as a problem', async () => {
    api.transcribeDictation.mockResolvedValue({ text: '' });
    const { result } = renderHook(() => useDictation());
    await waitFor(() => expect(result.current.offered).toBe(true));
    await act(async () => {
      await result.current.start();
    });
    await act(async () => {
      result.current.stop();
    });
    await waitFor(() => expect(result.current.recording).toBe(false));
    expect(result.current.problem).toBe('');
  });

  it('says so when the microphone is refused', async () => {
    vi.stubGlobal('navigator', {
      mediaDevices: { getUserMedia: vi.fn().mockRejectedValue(new Error('denied')) },
    });
    const { result } = renderHook(() => useDictation());
    await waitFor(() => expect(result.current.offered).toBe(true));
    await act(async () => {
      await result.current.start();
    });
    expect(result.current.recording).toBe(false);
    expect(result.current.problem).toMatch(/microphone/i);
  });

  it('is not offered at all where the browser cannot record', async () => {
    vi.stubGlobal('navigator', {});
    const { result } = renderHook(() => useDictation());
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(result.current.offered).toBe(false);
    // Nor is the agent asked: there is nothing it could answer that
    // would make a microphone appear.
    expect(api.dictationOffered).not.toHaveBeenCalled();
  });
});

describe('asking for the microphone', () => {
  it('says it is asking while it waits for an answer', async () => {
    let allow: (s: unknown) => void = () => {};
    vi.stubGlobal('navigator', {
      mediaDevices: {
        getUserMedia: vi.fn(() => new Promise((resolve) => { allow = resolve; })),
      },
    });
    const { result } = renderHook(() => useDictation());
    await waitFor(() => expect(result.current.offered).toBe(true));
    act(() => { void result.current.start(); });
    await waitFor(() => expect(result.current.working).toBe(true));
    allow({ getTracks: () => [{ stop: stopTrack }] });
  });

  it('gives up rather than waiting on an answer that never comes', async () => {
    vi.useFakeTimers();
    vi.stubGlobal('navigator', {
      mediaDevices: { getUserMedia: vi.fn(() => new Promise(() => {})) },
    });
    const { result } = renderHook(() => useDictation());
    await vi.waitFor(() => expect(result.current.offered).toBe(true));
    act(() => { void result.current.start(); });
    await act(async () => { await vi.advanceTimersByTimeAsync(20000); });
    expect(result.current.working).toBe(false);
    expect(result.current.problem).toMatch(/microphone/i);
    vi.useRealTimers();
  });
});

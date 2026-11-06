import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { useReadAloud } from './useReadAloud';

class FakeUtterance {
  text: string;
  lang = '';
  voice: { name: string } | null = null;
  onend: (() => void) | null = null;
  onerror: (() => void) | null = null;
  constructor(text: string) {
    this.text = text;
  }
}

const speaker = (name: string, lang: string, localService: boolean) =>
  ({ name, lang, localService }) as unknown as SpeechSynthesisVoice;

const ON_THIS_MACHINE = [
  speaker('Alex', 'en-US', true),
  speaker('Amélie', 'fr-FR', true),
];

function fakeVoice(voices: SpeechSynthesisVoice[] = ON_THIS_MACHINE) {
  const spoken: FakeUtterance[] = [];
  let listed = voices;
  const listeners: Array<() => void> = [];
  const synth = {
    speak: vi.fn((u: FakeUtterance) => spoken.push(u)),
    cancel: vi.fn(),
    getVoices: () => listed,
    addEventListener: (_: string, fn: () => void) => listeners.push(fn),
    removeEventListener: vi.fn(),
  };
  vi.stubGlobal('speechSynthesis', synth);
  vi.stubGlobal('SpeechSynthesisUtterance', FakeUtterance);
  const arrive = (later: SpeechSynthesisVoice[]) => {
    listed = later;
    listeners.forEach((fn) => fn());
  };
  return { synth, spoken, arrive };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('useReadAloud', () => {
  it('offers itself when the browser can speak', () => {
    fakeVoice();
    const { result } = renderHook(() => useReadAloud('Hello there.', 'en'));
    expect(result.current.available).toBe(true);
  });

  it('stays out of the way where the browser cannot speak', () => {
    vi.stubGlobal('speechSynthesis', undefined);
    const { result } = renderHook(() => useReadAloud('Hello there.', 'en'));
    expect(result.current.available).toBe(false);
  });

  it('has nothing to offer for a message with no prose', () => {
    fakeVoice();
    const { result } = renderHook(() => useReadAloud('```\nx = 1\n```', 'en'));
    expect(result.current.available).toBe(false);
  });

  it('speaks the prose, not the markdown', () => {
    const { spoken } = fakeVoice();
    const { result } = renderHook(() => useReadAloud('## Done\n\nAll **good**.', 'en'));
    act(() => result.current.toggle());
    expect(spoken[0].text).toBe('Done. All good.');
  });

  it('speaks in the language the reader is reading', () => {
    const { spoken } = fakeVoice();
    const { result } = renderHook(() => useReadAloud('Bonjour.', 'fr'));
    act(() => result.current.toggle());
    expect(spoken[0].lang).toBe('fr');
  });

  it('says that it is speaking while it speaks', () => {
    fakeVoice();
    const { result } = renderHook(() => useReadAloud('Hello.', 'en'));
    act(() => result.current.toggle());
    expect(result.current.speaking).toBe(true);
  });

  it('stops when asked a second time', () => {
    const { synth } = fakeVoice();
    const { result } = renderHook(() => useReadAloud('Hello.', 'en'));
    act(() => result.current.toggle());
    act(() => result.current.toggle());
    expect(synth.cancel).toHaveBeenCalled();
    expect(result.current.speaking).toBe(false);
  });

  it('knows when it has reached the end', () => {
    const { spoken } = fakeVoice();
    const { result } = renderHook(() => useReadAloud('Hello.', 'en'));
    act(() => result.current.toggle());
    act(() => spoken[0].onend?.());
    expect(result.current.speaking).toBe(false);
  });

  it('does not claim to be speaking after a voice fails', () => {
    const { spoken } = fakeVoice();
    const { result } = renderHook(() => useReadAloud('Hello.', 'en'));
    act(() => result.current.toggle());
    act(() => spoken[0].onerror?.());
    expect(result.current.speaking).toBe(false);
  });

  it('falls silent when the reader navigates away', () => {
    const { synth } = fakeVoice();
    const { result, unmount } = renderHook(() => useReadAloud('Hello.', 'en'));
    act(() => result.current.toggle());
    unmount();
    expect(synth.cancel).toHaveBeenCalled();
  });

  it('will not read with a voice that is really a service', () => {
    fakeVoice([speaker('Cloud', 'en-US', false)]);
    const { result } = renderHook(() => useReadAloud('Hello.', 'en'));
    expect(result.current.available).toBe(false);
  });

  it('reads with the voice that stays on this machine', () => {
    const { spoken } = fakeVoice();
    const { result } = renderHook(() => useReadAloud('Hello.', 'en'));
    act(() => result.current.toggle());
    expect(spoken[0].voice?.name).toBe('Alex');
  });

  it('offers itself once the browser has finished listing its voices', () => {
    const { arrive } = fakeVoice([]);
    const { result } = renderHook(() => useReadAloud('Hello.', 'en'));
    expect(result.current.available).toBe(false);
    act(() => arrive(ON_THIS_MACHINE));
    expect(result.current.available).toBe(true);
  });

  it('does not cancel anything it never started', () => {
    const { synth } = fakeVoice();
    const { unmount } = renderHook(() => useReadAloud('Hello.', 'en'));
    unmount();
    expect(synth.cancel).not.toHaveBeenCalled();
  });
});

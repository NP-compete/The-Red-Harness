import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ReadAloudButton } from './ReadAloudButton';

class FakeUtterance {
  text: string;
  lang = '';
  onend: (() => void) | null = null;
  onerror: (() => void) | null = null;
  constructor(text: string) {
    this.text = text;
  }
}

const ON_THIS_MACHINE = [
  { name: 'Alex', lang: 'en-US', localService: true },
] as unknown as SpeechSynthesisVoice[];

function canSpeak(voices = ON_THIS_MACHINE) {
  const spoken: FakeUtterance[] = [];
  vi.stubGlobal('speechSynthesis', {
    speak: vi.fn((u: FakeUtterance) => spoken.push(u)),
    cancel: vi.fn(),
    getVoices: () => voices,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  });
  vi.stubGlobal('SpeechSynthesisUtterance', FakeUtterance);
  return spoken;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('ReadAloudButton', () => {
  it('offers to read the answer out', () => {
    canSpeak();
    render(<ReadAloudButton text="All done." />);
    expect(screen.getByRole('button', { name: /read aloud/i })).toBeInTheDocument();
  });

  it('reads the answer when pressed', async () => {
    const spoken = canSpeak();
    render(<ReadAloudButton text="All done." />);
    await userEvent.click(screen.getByRole('button', { name: /read aloud/i }));
    expect(spoken[0].text).toBe('All done.');
  });

  it('offers to stop once it is reading', async () => {
    canSpeak();
    render(<ReadAloudButton text="All done." />);
    await userEvent.click(screen.getByRole('button', { name: /read aloud/i }));
    expect(screen.getByRole('button', { name: /stop reading/i })).toBeInTheDocument();
  });

  it('is not there at all when the browser has no voice', () => {
    vi.stubGlobal('speechSynthesis', undefined);
    render(<ReadAloudButton text="All done." />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('is not there when every voice would send the words away', () => {
    canSpeak([{ name: 'Cloud', lang: 'en-US', localService: false }] as unknown as SpeechSynthesisVoice[]);
    render(<ReadAloudButton text="All done." />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('is not there for an answer with nothing to say', () => {
    canSpeak();
    render(<ReadAloudButton text={'```\nx = 1\n```'} />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});

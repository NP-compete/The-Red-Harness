import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { InputForm } from './InputForm';

const dictation = vi.hoisted(() => ({
  state: {
    offered: true,
    recording: false,
    working: false,
    problem: '',
    start: vi.fn(),
    stop: vi.fn(),
  },
  useDictation: vi.fn(),
}));

vi.mock('../hooks/useDictation', () => ({
  useDictation: (onText?: (text: string) => void) => {
    dictation.useDictation(onText);
    return dictation.state;
  },
}));

function show() {
  return render(<InputForm onSubmit={vi.fn()} isLoading={false} onCancel={vi.fn()} />);
}

beforeEach(() => {
  dictation.state = {
    offered: true,
    recording: false,
    working: false,
    problem: '',
    start: vi.fn(),
    stop: vi.fn(),
  };
  dictation.useDictation.mockClear();
});

afterEach(() => {
  vi.clearAllMocks();
});

describe('dictating into the composer', () => {
  it('offers to listen when the deployment does speech', () => {
    show();
    expect(screen.getByRole('button', { name: /dictate|speak/i })).toBeInTheDocument();
  });

  it('offers nothing when the deployment does not', () => {
    dictation.state.offered = false;
    show();
    expect(screen.queryByRole('button', { name: /dictate|speak/i })).not.toBeInTheDocument();
  });

  it('starts listening when asked', () => {
    show();
    fireEvent.click(screen.getByRole('button', { name: /dictate|speak/i }));
    expect(dictation.state.start).toHaveBeenCalled();
  });

  it('stops listening when asked again', () => {
    dictation.state.recording = true;
    show();
    fireEvent.click(screen.getByRole('button', { name: /stop/i }));
    expect(dictation.state.stop).toHaveBeenCalled();
  });

  it('says it is listening while it is', () => {
    dictation.state.recording = true;
    show();
    expect(screen.getByRole('button', { name: /stop/i })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
  });

  it('puts what was said in the composer rather than sending it', async () => {
    const onSubmit = vi.fn();
    render(<InputForm onSubmit={onSubmit} isLoading={false} onCancel={vi.fn()} />);
    const heard = dictation.useDictation.mock.calls[0][0] as (text: string) => void;
    heard('book the room');
    await waitFor(() =>
      expect(screen.getByRole('textbox')).toHaveValue('book the room'),
    );
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('adds to what is already typed rather than replacing it', async () => {
    render(<InputForm onSubmit={vi.fn()} isLoading={false} onCancel={vi.fn()} />);
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Please' } });
    const heard = dictation.useDictation.mock.calls[0][0] as (text: string) => void;
    heard('book the room');
    await waitFor(() =>
      expect(screen.getByRole('textbox')).toHaveValue('Please book the room'),
    );
  });

  it('says why nothing arrived', () => {
    dictation.state.problem = 'No microphone is available.';
    show();
    expect(screen.getByText('No microphone is available.')).toBeInTheDocument();
  });
});

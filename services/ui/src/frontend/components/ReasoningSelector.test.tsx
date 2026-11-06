import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ReasoningSelector } from './ReasoningSelector';
import type { ReasoningProfile } from '../lib/reasoning-choice';

const OFFERED: ReasoningProfile[] = [
  { name: 'fast', effort: 'low' },
  { name: 'balanced', effort: 'medium' },
  { name: 'accurate', effort: 'high' },
];

describe('when there is no choice to make', () => {
  it('renders nothing at all when none are offered', () => {
    // An empty menu is worse than no menu: it says a choice
    // exists and then refuses to let anybody make it.
    const { container } = render(
      <ReasoningSelector threadId="t1" offered={[]} onChoose={vi.fn()} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('renders nothing when only one is offered', () => {
    const { container } = render(
      <ReasoningSelector threadId="t1" offered={[OFFERED[0]]} onChoose={vi.fn()} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});

describe('when there is', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('shows a shipped profile under its written name', () => {
    // "Accurate", not "accurate". A deployment's own profiles
    // keep whatever they were called, because the catalogue
    // cannot know about them.
    render(<ReasoningSelector threadId="t1" offered={OFFERED} onChoose={vi.fn()} />);
    expect(screen.getByRole('option', { name: 'Accurate' })).toBeTruthy();
  });

  it('shows a profile it has no name for exactly as declared', () => {
    render(
      <ReasoningSelector
        threadId="t1"
        offered={[...OFFERED, { name: 'overnight', effort: 'high' }]}
        onChoose={vi.fn()}
      />,
    );
    expect(screen.getByRole('option', { name: 'overnight' })).toBeTruthy();
  });

  it('offers each way of answering', () => {
    render(<ReasoningSelector threadId="t1" offered={OFFERED} onChoose={vi.fn()} />);
    for (const one of OFFERED) {
      expect(screen.getByRole('option', { name: new RegExp(one.name, 'i') })).toBeTruthy();
    }
  });

  it('starts on the agent default rather than guessing one', () => {
    // Nothing chosen means the agent decides, which is what
    // happened before this control existed.
    render(<ReasoningSelector threadId="t1" offered={OFFERED} onChoose={vi.fn()} />);
    expect(screen.getByRole('combobox')).toHaveValue('');
  });

  it('is named, so it can be found by somebody not using a mouse', () => {
    render(<ReasoningSelector threadId="t1" offered={OFFERED} onChoose={vi.fn()} />);
    expect(screen.getByRole('combobox')).toHaveAccessibleName();
  });

  it('tells the caller what was picked', async () => {
    const onChoose = vi.fn();
    render(<ReasoningSelector threadId="t1" offered={OFFERED} onChoose={onChoose} />);
    await userEvent.selectOptions(screen.getByRole('combobox'), 'accurate');
    expect(onChoose).toHaveBeenCalledWith('accurate');
  });

  it('remembers the pick for this thread', async () => {
    const { unmount } = render(
      <ReasoningSelector threadId="t1" offered={OFFERED} onChoose={vi.fn()} />,
    );
    await userEvent.selectOptions(screen.getByRole('combobox'), 'accurate');
    unmount();

    render(<ReasoningSelector threadId="t1" offered={OFFERED} onChoose={vi.fn()} />);
    expect(screen.getByRole('combobox')).toHaveValue('accurate');
  });

  it('does not carry the pick into another thread', async () => {
    const { unmount } = render(
      <ReasoningSelector threadId="t1" offered={OFFERED} onChoose={vi.fn()} />,
    );
    await userEvent.selectOptions(screen.getByRole('combobox'), 'accurate');
    unmount();

    render(<ReasoningSelector threadId="t2" offered={OFFERED} onChoose={vi.fn()} />);
    expect(screen.getByRole('combobox')).toHaveValue('');
  });

  it('falls back to the default when the pick is withdrawn', async () => {
    const { unmount } = render(
      <ReasoningSelector threadId="t1" offered={OFFERED} onChoose={vi.fn()} />,
    );
    await userEvent.selectOptions(screen.getByRole('combobox'), 'accurate');
    unmount();

    render(
      <ReasoningSelector threadId="t1" offered={[OFFERED[0], OFFERED[1]]} onChoose={vi.fn()} />,
    );
    expect(screen.getByRole('combobox')).toHaveValue('');
  });
});

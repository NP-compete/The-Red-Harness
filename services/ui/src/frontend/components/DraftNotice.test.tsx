import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { DraftNotice } from './DraftNotice';
import { draftStorage } from '../services/draftStorage';

describe('DraftNotice', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date('2026-03-01T12:00:00Z'));
  });

  afterEach(() => vi.useRealTimers());

  it('says nothing when nothing was left unsent', () => {
    const { container } = render(<DraftNotice threadId="t1" onRestore={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('offers back an unsent message', () => {
    draftStorage.save('t1', 'half a question');
    render(<DraftNotice threadId="t1" onRestore={vi.fn()} />);
    expect(screen.getByText('You have an unsent message here')).toBeInTheDocument();
  });

  it('shows what was written', () => {
    draftStorage.save('t1', 'half a question');
    render(<DraftNotice threadId="t1" onRestore={vi.fn()} />);
    expect(screen.getByText('half a question')).toBeInTheDocument();
  });

  it('shortens a long draft rather than filling the view with it', () => {
    draftStorage.save('t1', 'x'.repeat(200));
    render(<DraftNotice threadId="t1" onRestore={vi.fn()} />);
    expect(screen.getByText(`${'x'.repeat(80)}…`)).toBeInTheDocument();
  });

  it('puts the words back when asked', async () => {
    draftStorage.save('t1', 'half a question');
    const onRestore = vi.fn();
    render(<DraftNotice threadId="t1" onRestore={onRestore} />);
    await userEvent.click(screen.getByRole('button', { name: 'Restore' }));
    expect(onRestore).toHaveBeenCalledWith('half a question');
  });

  it('stops offering once restored', async () => {
    draftStorage.save('t1', 'half a question');
    render(<DraftNotice threadId="t1" onRestore={vi.fn()} />);
    await userEvent.click(screen.getByRole('button', { name: 'Restore' }));
    expect(screen.queryByText('You have an unsent message here')).not.toBeInTheDocument();
  });

  it('throws the draft away only when asked', async () => {
    draftStorage.save('t1', 'half a question');
    render(<DraftNotice threadId="t1" onRestore={vi.fn()} />);
    await userEvent.click(screen.getByRole('button', { name: 'Discard' }));
    expect(draftStorage.load('t1')).toBeNull();
  });

  it('keeps the draft while the notice is merely shown', () => {
    draftStorage.save('t1', 'half a question');
    render(<DraftNotice threadId="t1" onRestore={vi.fn()} />);
    expect(draftStorage.load('t1')?.text).toBe('half a question');
  });

  it('ignores a draft belonging to another conversation', () => {
    draftStorage.save('t2', 'half a question');
    const { container } = render(<DraftNotice threadId="t1" onRestore={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });
});

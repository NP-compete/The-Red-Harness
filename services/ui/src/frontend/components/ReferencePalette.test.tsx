import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { ReferencePalette } from './ReferencePalette';

const KNOWN = {
  subagents: [{ name: 'curator', about: 'Finds data worth trusting' }],
  documents: [{ name: 'notes.md', about: '1.2 kB' }],
};

const show = (input: string, onPick = vi.fn()) => {
  render(<ReferencePalette input={input} known={KNOWN} onPick={onPick} />);
  return onPick;
};

describe('ReferencePalette', () => {
  it('shows nothing until something is being referenced', () => {
    const { container } = render(
      <ReferencePalette input="what is the fee" known={KNOWN} onPick={vi.fn()} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('offers a specialist by name', () => {
    show('ask @');
    expect(screen.getByText('@curator')).toBeInTheDocument();
  });

  it('says what the specialist is for', () => {
    show('ask @');
    expect(screen.getByText('Finds data worth trusting')).toBeInTheDocument();
  });

  it('offers a document by name', () => {
    show('see #');
    expect(screen.getByText('#notes.md')).toBeInTheDocument();
  });

  it('does not offer documents when a specialist is being named', () => {
    show('ask @');
    expect(screen.queryByText('#notes.md')).not.toBeInTheDocument();
  });

  it('hands back the finished sentence when one is picked', () => {
    const onPick = show('ask @cur');
    fireEvent.click(screen.getByText('@curator'));
    expect(onPick).toHaveBeenCalledWith('ask @curator ');
  });

  it('can be picked with the keyboard alone', () => {
    const onPick = show('ask @cur');
    fireEvent.keyDown(screen.getByText('@curator').closest('li')!, { key: 'Enter' });
    expect(onPick).toHaveBeenCalledWith('ask @curator ');
  });

  it('says when nothing matches rather than showing an empty box', () => {
    show('ask @zzz');
    expect(screen.getByText(/nothing here is called/i)).toBeInTheDocument();
  });

  it('can be dismissed', () => {
    show('ask @');
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.queryByText('@curator')).not.toBeInTheDocument();
  });

  it('comes back once the typing moves on', () => {
    const { rerender } = render(
      <ReferencePalette input="ask @" known={KNOWN} onPick={vi.fn()} />,
    );
    fireEvent.keyDown(window, { key: 'Escape' });
    rerender(<ReferencePalette input="ask @cu" known={KNOWN} onPick={vi.fn()} />);
    expect(screen.getByText('@curator')).toBeInTheDocument();
  });
});

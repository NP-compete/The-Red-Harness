import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { CommandPalette } from './CommandPalette';

const commands = [
  { name: 'explain', help: 'Explain the last answer in more detail' },
  { name: 'summarise', help: 'Sum up this conversation' },
];

describe('CommandPalette', () => {
  it('stays out of the way of an ordinary message', () => {
    const { container } = render(
      <CommandPalette input="what is the limit" commands={commands} onPick={vi.fn()} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('opens on a slash', () => {
    render(<CommandPalette input="/" commands={commands} onPick={vi.fn()} />);
    expect(screen.getByRole('listbox')).toBeInTheDocument();
  });

  it('lists every command on a bare slash', () => {
    render(<CommandPalette input="/" commands={commands} onPick={vi.fn()} />);
    expect(screen.getAllByRole('option')).toHaveLength(2);
  });

  it('narrows as the name is typed', () => {
    render(<CommandPalette input="/sum" commands={commands} onPick={vi.fn()} />);
    expect(screen.getAllByRole('option')).toHaveLength(1);
  });

  it('shows what each command does', () => {
    render(<CommandPalette input="/sum" commands={commands} onPick={vi.fn()} />);
    expect(screen.getByText('Sum up this conversation')).toBeInTheDocument();
  });

  it('says plainly when nothing matches', () => {
    render(<CommandPalette input="/zzz" commands={commands} onPick={vi.fn()} />);
    expect(screen.getByText('No command matches "zzz"')).toBeInTheDocument();
  });

  it('gets out of the way once an argument is being typed', () => {
    const { container } = render(
      <CommandPalette input="/summarise the third" commands={commands} onPick={vi.fn()} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('hands back the command when one is picked', async () => {
    const onPick = vi.fn();
    render(<CommandPalette input="/sum" commands={commands} onPick={onPick} />);
    await userEvent.click(screen.getByRole('option'));
    expect(onPick).toHaveBeenCalledWith('summarise');
  });

  it('shows nothing when the agent offers no commands', () => {
    const { container } = render(<CommandPalette input="/" commands={[]} onPick={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });
});

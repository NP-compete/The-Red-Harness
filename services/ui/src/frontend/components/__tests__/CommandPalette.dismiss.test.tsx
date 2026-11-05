import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { CommandPalette } from '../CommandPalette';

const COMMANDS = [
  { name: 'summarise', help: 'Sum up this conversation' },
  { name: 'shorter', help: 'Rewrite the last answer more briefly' },
];

describe('CommandPalette — getting rid of it', () => {
  it('shows the commands while a slash is being typed', () => {
    render(<CommandPalette input="/sum" commands={COMMANDS} onPick={vi.fn()} />);
    expect(screen.getByRole('listbox')).toBeInTheDocument();
  });

  it('closes when escape is pressed', async () => {
    render(<CommandPalette input="/sum" commands={COMMANDS} onPick={vi.fn()} />);
    await userEvent.keyboard('{Escape}');
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
  });

  it('comes back when the typing moves on', async () => {
    const { rerender } = render(
      <CommandPalette input="/sum" commands={COMMANDS} onPick={vi.fn()} />,
    );
    await userEvent.keyboard('{Escape}');
    rerender(<CommandPalette input="/summ" commands={COMMANDS} onPick={vi.fn()} />);
    expect(screen.getByRole('listbox')).toBeInTheDocument();
  });

  it('stays shut while the same text is still there', async () => {
    const { rerender } = render(
      <CommandPalette input="/sum" commands={COMMANDS} onPick={vi.fn()} />,
    );
    await userEvent.keyboard('{Escape}');
    rerender(<CommandPalette input="/sum" commands={COMMANDS} onPick={vi.fn()} />);
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
  });

  it('still picks a command that is clicked', async () => {
    const onPick = vi.fn();
    render(<CommandPalette input="/sum" commands={COMMANDS} onPick={onPick} />);
    await userEvent.click(screen.getByText('/summarise'));
    expect(onPick).toHaveBeenCalledWith('summarise');
  });
});

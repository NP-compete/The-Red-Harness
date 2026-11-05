import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { ThreadSelectionBar } from './ThreadSelectionBar';

function bar(overrides = {}) {
  return {
    count: 2,
    summary: '2 selected',
    beyondThisPage: false,
    onSelectAll: vi.fn(),
    onClear: vi.fn(),
    onDelete: vi.fn(),
    ...overrides,
  };
}

describe('ThreadSelectionBar', () => {
  it('says how much is picked', () => {
    render(<ThreadSelectionBar {...bar()} />);
    expect(screen.getByText('2 selected')).toBeInTheDocument();
  });

  it('shows nothing while nothing is picked', () => {
    const { container } = render(
      <ThreadSelectionBar {...bar({ count: 0, summary: 'Nothing selected' })} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('offers to delete what is picked', async () => {
    const onDelete = vi.fn();
    render(<ThreadSelectionBar {...bar({ onDelete })} />);
    await userEvent.click(screen.getByRole('button', { name: 'Delete 2' }));
    expect(onDelete).toHaveBeenCalled();
  });

  it('names how many a delete will take', () => {
    render(<ThreadSelectionBar {...bar({ count: 7, summary: '7 selected' })} />);
    expect(screen.getByRole('button', { name: 'Delete 7' })).toBeInTheDocument();
  });

  it('offers a way out', async () => {
    const onClear = vi.fn();
    render(<ThreadSelectionBar {...bar({ onClear })} />);
    await userEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(onClear).toHaveBeenCalled();
  });

  it('offers to reach everything, not just the visible rows', async () => {
    const onSelectAll = vi.fn();
    render(<ThreadSelectionBar {...bar({ onSelectAll })} />);
    await userEvent.click(screen.getByRole('button', { name: 'Select all' }));
    expect(onSelectAll).toHaveBeenCalled();
  });

  it('warns plainly once a selection reaches past what is on screen', () => {
    render(<ThreadSelectionBar {...bar({ beyondThisPage: true })} />);
    expect(
      screen.getByText('This includes conversations not shown here'),
    ).toBeInTheDocument();
  });

  it('adds no such warning to a handful of picked rows', () => {
    render(<ThreadSelectionBar {...bar()} />);
    expect(screen.queryByText(/not shown here/)).not.toBeInTheDocument();
  });

  it('stops offering select-all once everything is already picked', () => {
    render(<ThreadSelectionBar {...bar({ beyondThisPage: true })} />);
    expect(screen.queryByRole('button', { name: 'Select all' })).not.toBeInTheDocument();
  });
});

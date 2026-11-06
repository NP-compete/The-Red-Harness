import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { TagFilter } from './TagFilter';

const api = vi.hoisted(() => ({ listTags: vi.fn(), threadsWithTag: vi.fn() }));
vi.mock('../services/tags-api', () => api);

beforeEach(() => {
  vi.clearAllMocks();
  api.listTags.mockResolvedValue([
    { tag: 'billing', threads: 4 },
    { tag: 'travel', threads: 1 },
  ]);
  api.threadsWithTag.mockResolvedValue([
    { id: 't1', title: 'Invoices', tags: ['billing'], updatedAt: null },
  ]);
});

describe('TagFilter', () => {
  it('shows nothing when no tag has ever been used', async () => {
    api.listTags.mockResolvedValue([]);
    const { container } = render(<TagFilter onFilter={vi.fn()} />);
    await vi.waitFor(() => expect(api.listTags).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it('offers each tag that has been used', async () => {
    render(<TagFilter onFilter={vi.fn()} />);
    expect(await screen.findByRole('button', { name: /billing/ })).toBeInTheDocument();
  });

  it('says how many conversations carry each tag', async () => {
    render(<TagFilter onFilter={vi.fn()} />);
    expect(await screen.findByRole('button', { name: 'billing 4' })).toBeInTheDocument();
  });

  it('puts the most used tag first', async () => {
    api.listTags.mockResolvedValue([
      { tag: 'travel', threads: 1 },
      { tag: 'billing', threads: 4 },
    ]);
    render(<TagFilter onFilter={vi.fn()} />);
    await screen.findByRole('button', { name: /billing/ });
    const names = screen.getAllByRole('button').map((b) => b.textContent);
    expect(names[0]).toContain('billing');
  });

  it('hands back the conversations carrying a chosen tag', async () => {
    const onFilter = vi.fn();
    render(<TagFilter onFilter={onFilter} />);
    await userEvent.click(await screen.findByRole('button', { name: /billing/ }));
    await vi.waitFor(() => expect(onFilter).toHaveBeenCalledWith('billing', ['t1']));
  });

  it('marks the tag being filtered by', async () => {
    render(<TagFilter onFilter={vi.fn()} />);
    const billing = await screen.findByRole('button', { name: /billing/ });
    await userEvent.click(billing);
    expect(billing).toHaveAttribute('aria-pressed', 'true');
  });

  it('clears the filter when the same tag is pressed again', async () => {
    const onFilter = vi.fn();
    render(<TagFilter onFilter={onFilter} />);
    const billing = await screen.findByRole('button', { name: /billing/ });
    await userEvent.click(billing);
    await userEvent.click(billing);
    expect(onFilter).toHaveBeenLastCalledWith(null, null);
  });

  it('does not ask the agent again when clearing', async () => {
    render(<TagFilter onFilter={vi.fn()} />);
    const billing = await screen.findByRole('button', { name: /billing/ });
    await userEvent.click(billing);
    await userEvent.click(billing);
    expect(api.threadsWithTag).toHaveBeenCalledTimes(1);
  });
});

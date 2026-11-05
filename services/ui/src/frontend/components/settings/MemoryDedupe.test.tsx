import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { MemoryDedupe } from './MemoryDedupe';

const api = vi.hoisted(() => ({ removeDuplicateMemories: vi.fn() }));
vi.mock('../../services/memory-dedupe', () => api);

beforeEach(() => {
  vi.clearAllMocks();
  api.removeDuplicateMemories.mockResolvedValue({ removed: 2, remaining: 3 });
});

describe('MemoryDedupe', () => {
  it('offers to collapse repeats', () => {
    render(<MemoryDedupe onChanged={vi.fn()} />);
    expect(screen.getByRole('button', { name: /remove duplicates/i })).toBeInTheDocument();
  });

  it('says how many it took out', async () => {
    render(<MemoryDedupe onChanged={vi.fn()} />);
    await userEvent.click(screen.getByRole('button', { name: /remove duplicates/i }));
    expect(await screen.findByText(/removed 2/i)).toBeInTheDocument();
  });

  it('says plainly when there were none', async () => {
    api.removeDuplicateMemories.mockResolvedValue({ removed: 0, remaining: 2 });
    render(<MemoryDedupe onChanged={vi.fn()} />);
    await userEvent.click(screen.getByRole('button', { name: /remove duplicates/i }));
    expect(await screen.findByText(/nothing was repeated/i)).toBeInTheDocument();
  });

  it('counts a single duplicate in the singular', async () => {
    api.removeDuplicateMemories.mockResolvedValue({ removed: 1, remaining: 4 });
    render(<MemoryDedupe onChanged={vi.fn()} />);
    await userEvent.click(screen.getByRole('button', { name: /remove duplicates/i }));
    expect(await screen.findByText(/removed 1 memory\b/i)).toBeInTheDocument();
  });

  it('asks the list to reload once something changed', async () => {
    const onChanged = vi.fn();
    render(<MemoryDedupe onChanged={onChanged} />);
    await userEvent.click(screen.getByRole('button', { name: /remove duplicates/i }));
    await vi.waitFor(() => expect(onChanged).toHaveBeenCalled());
  });

  it('leaves the list alone when nothing was removed', async () => {
    api.removeDuplicateMemories.mockResolvedValue({ removed: 0, remaining: 2 });
    const onChanged = vi.fn();
    render(<MemoryDedupe onChanged={onChanged} />);
    await userEvent.click(screen.getByRole('button', { name: /remove duplicates/i }));
    await screen.findByText(/nothing was repeated/i);
    expect(onChanged).not.toHaveBeenCalled();
  });

  it('says so when it could not be done', async () => {
    api.removeDuplicateMemories.mockResolvedValue(null);
    render(<MemoryDedupe onChanged={vi.fn()} />);
    await userEvent.click(screen.getByRole('button', { name: /remove duplicates/i }));
    expect(await screen.findByText(/could not be checked/i)).toBeInTheDocument();
  });
});

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ReindexControl } from './ReindexControl';

const api = vi.hoisted(() => ({ reindexThreads: vi.fn() }));
vi.mock('../../services/search-reindex', () => api);

beforeEach(() => {
  vi.clearAllMocks();
  api.reindexThreads.mockResolvedValue(14);
});

describe('ReindexControl', () => {
  it('offers to rebuild the index', () => {
    render(<ReindexControl />);
    expect(screen.getByRole('button', { name: /rebuild search index/i })).toBeInTheDocument();
  });

  it('says nothing about results before it has run', () => {
    render(<ReindexControl />);
    expect(screen.queryByText(/indexed/i)).not.toBeInTheDocument();
  });

  it('rebuilds when pressed', async () => {
    render(<ReindexControl />);
    await userEvent.click(screen.getByRole('button', { name: /rebuild search index/i }));
    expect(api.reindexThreads).toHaveBeenCalled();
  });

  it('says how many conversations were indexed', async () => {
    render(<ReindexControl />);
    await userEvent.click(screen.getByRole('button', { name: /rebuild search index/i }));
    expect(await screen.findByText('Indexed 14 conversations')).toBeInTheDocument();
  });

  it('counts one conversation properly', async () => {
    api.reindexThreads.mockResolvedValue(1);
    render(<ReindexControl />);
    await userEvent.click(screen.getByRole('button', { name: /rebuild search index/i }));
    expect(await screen.findByText('Indexed 1 conversation')).toBeInTheDocument();
  });

  it('says plainly when there was nothing to index', async () => {
    api.reindexThreads.mockResolvedValue(0);
    render(<ReindexControl />);
    await userEvent.click(screen.getByRole('button', { name: /rebuild search index/i }));
    expect(await screen.findByText('Nothing to index')).toBeInTheDocument();
  });

  it('says plainly when it could not be done', async () => {
    api.reindexThreads.mockResolvedValue(null);
    render(<ReindexControl />);
    await userEvent.click(screen.getByRole('button', { name: /rebuild search index/i }));
    expect(await screen.findByText(/could not rebuild/i)).toBeInTheDocument();
  });

  it('does not let it be pressed twice at once', async () => {
    let release: (value: number) => void = () => {};
    api.reindexThreads.mockReturnValue(new Promise<number>((r) => { release = r; }));
    render(<ReindexControl />);
    const button = screen.getByRole('button', { name: /rebuild search index/i });
    await userEvent.click(button);
    expect(button).toBeDisabled();
    release(3);
  });
});

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ShareControl } from './ShareControl';

const api = vi.hoisted(() => ({
  getShare: vi.fn(),
  createShare: vi.fn(),
  revokeShare: vi.fn(),
}));

vi.mock('../services/share-api', () => api);

const live = {
  shareId: 's1',
  scope: 'authenticated' as const,
  active: true,
  views: 3,
  expiresAt: new Date(Date.now() + 48 * 3600_000).toISOString(),
  path: '/shared/s1',
};

beforeEach(() => {
  api.getShare.mockResolvedValue(null);
  api.createShare.mockResolvedValue(live);
  api.revokeShare.mockResolvedValue(true);
});

describe('ShareControl', () => {
  it('offers to share a conversation that is not shared', async () => {
    render(<ShareControl threadId="t1" />);
    expect(await screen.findByRole('button', { name: /share/i })).toBeInTheDocument();
  });

  it('says nothing about views before anything is shared', async () => {
    render(<ShareControl threadId="t1" />);
    await screen.findByRole('button', { name: /share/i });
    expect(screen.queryByText(/opened/i)).not.toBeInTheDocument();
  });

  it('creates a link when asked', async () => {
    render(<ShareControl threadId="t1" />);
    await userEvent.click(await screen.findByRole('button', { name: /share/i }));
    expect(api.createShare).toHaveBeenCalledWith('t1', 'authenticated', expect.any(Number));
  });

  it('says who can open the link', async () => {
    api.getShare.mockResolvedValue(live);
    render(<ShareControl threadId="t1" />);
    expect(await screen.findByText('Anyone signed in')).toBeInTheDocument();
  });

  it('says how often it has been opened', async () => {
    api.getShare.mockResolvedValue(live);
    render(<ShareControl threadId="t1" />);
    expect(await screen.findByText('opened 3 times')).toBeInTheDocument();
  });

  it('says when it stops working', async () => {
    api.getShare.mockResolvedValue(live);
    render(<ShareControl threadId="t1" />);
    // The presenter words this as a phrase to follow "expires".
    expect(await screen.findByText('in 2 days')).toBeInTheDocument();
  });

  it('offers to take the link back', async () => {
    api.getShare.mockResolvedValue(live);
    render(<ShareControl threadId="t1" />);
    await userEvent.click(await screen.findByRole('button', { name: /revoke/i }));
    expect(api.revokeShare).toHaveBeenCalledWith('t1');
  });

  it('stops showing a revoked link as live', async () => {
    api.getShare.mockResolvedValue(live);
    render(<ShareControl threadId="t1" />);
    await userEvent.click(await screen.findByRole('button', { name: /revoke/i }));
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /share/i })).toBeInTheDocument(),
    );
  });

  it('warns plainly about a link anyone can open', async () => {
    api.getShare.mockResolvedValue({ ...live, scope: 'public' as const });
    render(<ShareControl threadId="t1" />);
    expect(await screen.findByText('Anyone with the link')).toBeInTheDocument();
  });
});

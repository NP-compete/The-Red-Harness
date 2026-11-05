import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { SharedLinks } from './SharedLinks';

const api = vi.hoisted(() => ({ listShares: vi.fn(), revokeShare: vi.fn() }));
vi.mock('../../services/share-api', () => api);

const soon = new Date(Date.now() + 48 * 3600_000).toISOString();

beforeEach(() => {
  api.listShares.mockResolvedValue([
    { shareId: 's1', threadId: 't1', title: 'Travel limits', scope: 'authenticated', active: true, views: 2, expiresAt: soon, path: '/shared/s1' },
  ]);
  api.revokeShare.mockResolvedValue(true);
});

describe('SharedLinks', () => {
  it('says plainly when nothing has been shared', async () => {
    api.listShares.mockResolvedValue([]);
    render(<SharedLinks />);
    expect(await screen.findByText(/nothing is shared/i)).toBeInTheDocument();
  });

  it('names each shared conversation', async () => {
    render(<SharedLinks />);
    expect(await screen.findByText('Travel limits')).toBeInTheDocument();
  });

  it('says who can open each link', async () => {
    render(<SharedLinks />);
    expect(await screen.findByText('Anyone signed in')).toBeInTheDocument();
  });

  it('says how often each was opened', async () => {
    render(<SharedLinks />);
    expect(await screen.findByText('opened 2 times')).toBeInTheDocument();
  });

  it('links to the shared page itself', async () => {
    render(<SharedLinks />);
    expect(await screen.findByRole('link', { name: /travel limits/i })).toHaveAttribute(
      'href',
      '/shared/s1',
    );
  });

  it('takes a link down when asked', async () => {
    render(<SharedLinks />);
    await userEvent.click(await screen.findByRole('button', { name: /revoke/i }));
    expect(api.revokeShare).toHaveBeenCalledWith('t1');
  });

  it('stops listing a link once it is taken down', async () => {
    render(<SharedLinks />);
    await userEvent.click(await screen.findByRole('button', { name: /revoke/i }));
    await waitFor(() => expect(screen.queryByText('Travel limits')).not.toBeInTheDocument());
  });

  it('marks a link anyone can open', async () => {
    api.listShares.mockResolvedValue([
      { shareId: 's2', threadId: 't2', title: 'Expenses', scope: 'public', active: true, views: 0, expiresAt: soon, path: '/shared/s2' },
    ]);
    render(<SharedLinks />);
    expect(await screen.findByText('Anyone with the link')).toBeInTheDocument();
  });

  it('leaves an expired link listed, so it can still be seen', async () => {
    api.listShares.mockResolvedValue([
      { shareId: 's3', threadId: 't3', title: 'Old one', scope: 'authenticated', active: true, views: 1, expiresAt: new Date(Date.now() - 3600_000).toISOString(), path: '/shared/s3' },
    ]);
    render(<SharedLinks />);
    expect(await screen.findByText('expired')).toBeInTheDocument();
  });

  const revoked = {
    shareId: 's2',
    threadId: 't2',
    title: 'Expenses',
    scope: 'authenticated',
    active: false,
    views: 4,
    expiresAt: soon,
    path: '/shared/s2',
  };

  it('does not offer to revoke a link that is already dead', async () => {
    api.listShares.mockResolvedValue([revoked]);
    render(<SharedLinks />);
    await screen.findByText('Expenses');
    expect(screen.queryByRole('button', { name: /revoke/i })).not.toBeInTheDocument();
  });

  it('says a dead link no longer works', async () => {
    api.listShares.mockResolvedValue([revoked]);
    render(<SharedLinks />);
    expect(await screen.findByText(/no longer works/i)).toBeInTheDocument();
  });

  it('still offers to revoke a link that works', async () => {
    render(<SharedLinks />);
    expect(await screen.findByRole('button', { name: /revoke/i })).toBeInTheDocument();
  });

  it('offers revoke only for the live link when both are listed', async () => {
    api.listShares.mockResolvedValue([
      { shareId: 's1', threadId: 't1', title: 'Travel limits', scope: 'authenticated', active: true, views: 2, expiresAt: soon, path: '/shared/s1' },
      revoked,
    ]);
    render(<SharedLinks />);
    await screen.findByText('Expenses');
    expect(screen.getAllByRole('button', { name: /revoke/i })).toHaveLength(1);
  });
});

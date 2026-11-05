import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { MyLibrary } from './MyLibrary';
import * as api from '../../services/knowledge-api';

const FULL = {
  documents: [{ id: 'user:1', title: 'Leave notes', bytes: 2048 }],
  used_bytes: 2048,
  limit_bytes: 10240,
};

function answering(report: unknown) {
  return vi.spyOn(api, 'readLibrary').mockResolvedValue(report as never);
}

describe('MyLibrary', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('says nothing while it is still asking', () => {
    vi.spyOn(api, 'readLibrary').mockReturnValue(new Promise(() => {}) as never);
    const { container } = render(<MyLibrary />);
    expect(container).toBeEmptyDOMElement();
  });

  describe('a deployment that does not keep personal documents', () => {
    it('shows nothing at all', async () => {
      // Not an empty list with an upload box. Offering a place
      // to put something retrieval will never search is the
      // defect this whole area exists to avoid.
      answering(null);
      const { container } = render(<MyLibrary />);
      await waitFor(() => expect(container).toBeEmptyDOMElement());
    });
  });

  describe('documents already there', () => {
    it('lists them', async () => {
      answering(FULL);
      render(<MyLibrary />);
      expect(await screen.findByText('Leave notes')).toBeInTheDocument();
    });

    it('shows how big each one is', async () => {
      answering(FULL);
      render(<MyLibrary />);
      expect(await screen.findByText('2.0 KB')).toBeInTheDocument();
    });

    it('shows how much room is left', async () => {
      answering(FULL);
      render(<MyLibrary />);
      expect(await screen.findByText(/2\.0 KB of 10\.0 KB/)).toBeInTheDocument();
    });
  });

  describe('an empty library', () => {
    it('says so rather than showing a bare box', async () => {
      answering({ documents: [], used_bytes: 0, limit_bytes: 10240 });
      render(<MyLibrary />);
      expect(await screen.findByText(/nothing here yet/i)).toBeInTheDocument();
    });
  });

  describe('when it is nearly full', () => {
    it('warns before the next upload is refused', async () => {
      answering({ ...FULL, used_bytes: 9728 });
      render(<MyLibrary />);
      expect(await screen.findByRole('status')).toBeInTheDocument();
    });

    it('does not warn with room to spare', async () => {
      answering(FULL);
      render(<MyLibrary />);
      await screen.findByText('Leave notes');
      expect(screen.queryByRole('status')).not.toBeInTheDocument();
    });
  });

  describe('removing one', () => {
    it('asks the agent to remove it', async () => {
      answering(FULL);
      const removing = vi.spyOn(api, 'removeFromLibrary').mockResolvedValue(true);
      render(<MyLibrary />);
      await userEvent.click(await screen.findByRole('button', { name: /remove leave notes/i }));
      expect(removing).toHaveBeenCalledWith('user:1');
    });

    it('stops showing it afterwards', async () => {
      answering(FULL);
      vi.spyOn(api, 'removeFromLibrary').mockResolvedValue(true);
      vi.spyOn(api, 'readLibrary').mockResolvedValueOnce(FULL as never).mockResolvedValue({
        documents: [],
        used_bytes: 0,
        limit_bytes: 10240,
      } as never);
      render(<MyLibrary />);
      await userEvent.click(await screen.findByRole('button', { name: /remove leave notes/i }));
      await waitFor(() => expect(screen.queryByText('Leave notes')).not.toBeInTheDocument());
    });

    it('keeps showing it when the agent refused', async () => {
      // Removing it from the list regardless would tell
      // somebody it is gone when it is not.
      answering(FULL);
      vi.spyOn(api, 'removeFromLibrary').mockResolvedValue(false);
      render(<MyLibrary />);
      await userEvent.click(await screen.findByRole('button', { name: /remove leave notes/i }));
      expect(await screen.findByText('Leave notes')).toBeInTheDocument();
    });
  });

  describe('adding one', () => {
    it('sends the title and the text', async () => {
      answering(FULL);
      const adding = vi.spyOn(api, 'addToLibrary').mockResolvedValue({ ok: true });
      render(<MyLibrary />);
      await userEvent.type(await screen.findByLabelText(/title/i), 'Expenses');
      await userEvent.type(screen.getByLabelText(/text/i), 'Claims over 750 need a receipt.');
      await userEvent.click(screen.getByRole('button', { name: /^add$/i }));
      expect(adding).toHaveBeenCalledWith('Expenses', 'Claims over 750 need a receipt.');
    });

    it('shows what the agent said when it refused', async () => {
      // The agent knows how much room is left. A generic
      // failure here sends somebody guessing.
      answering(FULL);
      vi.spyOn(api, 'addToLibrary').mockResolvedValue({
        ok: false,
        detail: '2048 of 10240 bytes used',
      });
      render(<MyLibrary />);
      await userEvent.type(await screen.findByLabelText(/title/i), 'Big');
      await userEvent.type(screen.getByLabelText(/text/i), 'x');
      await userEvent.click(screen.getByRole('button', { name: /^add$/i }));
      expect(await screen.findByText(/2048 of 10240 bytes used/)).toBeInTheDocument();
    });

    it('will not send an empty document', async () => {
      answering(FULL);
      const adding = vi.spyOn(api, 'addToLibrary').mockResolvedValue({ ok: true });
      render(<MyLibrary />);
      await userEvent.type(await screen.findByLabelText(/title/i), 'Empty');
      await userEvent.click(screen.getByRole('button', { name: /^add$/i }));
      expect(adding).not.toHaveBeenCalled();
    });
  });
});

describe('MyLibrary — what a team shares', () => {
  const SHARED = {
    documents: [],
    team: [
      { id: 'corpus:teams/platform/runbook.md', title: 'runbook', bytes: 512, team: 'platform' },
    ],
    used_bytes: 0,
    limit_bytes: 10240,
  };

  beforeEach(() => vi.restoreAllMocks());

  it('lists them', async () => {
    vi.spyOn(api, 'readLibrary').mockResolvedValue(SHARED as never);
    render(<MyLibrary />);
    expect(await screen.findByText('runbook')).toBeInTheDocument();
  });

  it('says which team it came from', async () => {
    vi.spyOn(api, 'readLibrary').mockResolvedValue(SHARED as never);
    render(<MyLibrary />);
    expect(await screen.findByText(/platform/)).toBeInTheDocument();
  });

  it('offers no way to remove one', async () => {
    // It comes from the configuration tree and returns on the
    // next sync. A delete button would confuse somebody for an
    // afternoon.
    vi.spyOn(api, 'readLibrary').mockResolvedValue(SHARED as never);
    render(<MyLibrary />);
    await screen.findByText('runbook');
    expect(screen.queryByRole('button', { name: /remove runbook/i })).not.toBeInTheDocument();
  });

  it('says nothing about teams when there are none', async () => {
    vi.spyOn(api, 'readLibrary').mockResolvedValue({
      documents: [], team: [], used_bytes: 0, limit_bytes: 10240,
    } as never);
    render(<MyLibrary />);
    await screen.findByText(/nothing here yet/i);
    expect(screen.queryByText(/shared with you/i)).not.toBeInTheDocument();
  });
});

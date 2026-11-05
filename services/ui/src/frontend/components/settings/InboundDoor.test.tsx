import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { InboundDoor } from './InboundDoor';
import * as api from '../../services/schema-version-api';

function answering(report: unknown) {
  return vi.spyOn(api, 'readInbound').mockResolvedValue(report as never);
}

const OPEN = {
  enabled: true,
  auth_mode: 'service_token',
  published_tools: 2,
  limits: { per_second: 2, burst: 10, daily_spend: '5.00' },
};

describe('InboundDoor', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('says nothing while it is still asking', () => {
    vi.spyOn(api, 'readInbound').mockReturnValue(new Promise(() => {}) as never);
    const { container } = render(<InboundDoor />);
    expect(container).toBeEmptyDOMElement();
  });

  describe('a door that is shut', () => {
    it('is not mentioned at all', async () => {
      // Every deployment has this shut. A row on every one of them
      // is a row nobody reads.
      answering({ enabled: false, auth_mode: '', published_tools: 0, limits: null });
      const { container } = render(<InboundDoor />);
      await waitFor(() => expect(container).toBeEmptyDOMElement());
    });
  });

  describe('a door that is open', () => {
    it('says so', async () => {
      answering(OPEN);
      render(<InboundDoor />);
      await waitFor(() => expect(screen.getByText(/open/i)).toBeInTheDocument());
    });

    it('shows the rate', async () => {
      answering(OPEN);
      render(<InboundDoor />);
      await waitFor(() => expect(screen.getByText(/2\/s, burst 10/)).toBeInTheDocument());
    });

    it('shows the daily cap', async () => {
      answering(OPEN);
      render(<InboundDoor />);
      await waitFor(() => expect(screen.getByText(/5\.00/)).toBeInTheDocument());
    });

    it('raises no alarm', async () => {
      answering(OPEN);
      render(<InboundDoor />);
      await waitFor(() => expect(screen.getByText(/open/i)).toBeInTheDocument());
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });
  });

  describe('a door that is open with no spend cap', () => {
    it('is flagged', async () => {
      // One caller away from the whole budget, and nothing else on
      // this page would show it.
      answering({ ...OPEN, limits: null });
      render(<InboundDoor />);
      expect(await screen.findByRole('alert')).toBeInTheDocument();
    });

    it('says what the risk is, not just that there is one', async () => {
      answering({ ...OPEN, limits: null });
      render(<InboundDoor />);
      expect(await screen.findByText(/budget/i)).toBeInTheDocument();
    });
  });

  describe('an agent that could not say', () => {
    it('shows nothing', async () => {
      answering(null);
      const { container } = render(<InboundDoor />);
      await waitFor(() => expect(container).toBeEmptyDOMElement());
    });
  });
});

describe('what an open door exposes without authentication', () => {
  it('says discovery is public', async () => {
    // An operator who opened this door should know the agent's
    // name and address can be fetched by anyone who can reach
    // it. Nothing else on the page says so.
    vi.spyOn(api, 'readInbound').mockResolvedValue(OPEN as never);
    render(<InboundDoor />);
    expect(await screen.findByText(/discoverable/i)).toBeInTheDocument();
  });

  it('says the capability list is not', async () => {
    // The half that matters: what the deployment does stays
    // behind authentication.
    vi.spyOn(api, 'readInbound').mockResolvedValue(OPEN as never);
    render(<InboundDoor />);
    expect(await screen.findByText(/not its capabilities/i)).toBeInTheDocument();
  });

  it('says nothing of the sort when the door is shut', async () => {
    vi.spyOn(api, 'readInbound').mockResolvedValue({
      enabled: false,
      auth_mode: '',
      published_tools: 0,
      limits: null,
    } as never);
    const { container } = render(<InboundDoor />);
    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });
});

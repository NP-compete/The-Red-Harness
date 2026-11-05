import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AlertBanner } from './AlertBanner';
import * as api from '../services/alerts-api';

function answering(report: unknown) {
  return vi.spyOn(api, 'readAlerts').mockResolvedValue(report as never);
}

const QUIET = { ok: true, breaches: [], thresholds: {}, unreadable: false };

describe('AlertBanner', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('says nothing while it is still asking', () => {
    vi.spyOn(api, 'readAlerts').mockReturnValue(new Promise(() => {}) as never);
    const { container } = render(<AlertBanner days={7} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('says nothing when nothing is over a limit', async () => {
    // A banner on every healthy window is a banner people stop
    // reading, which costs the one that mattered.
    answering(QUIET);
    const { container } = render(<AlertBanner days={7} />);
    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });

  it('says nothing when no limits are configured', async () => {
    answering({ ...QUIET, thresholds: { error_rate: null } });
    const { container } = render(<AlertBanner days={7} />);
    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });

  describe('something over a limit', () => {
    const breached = {
      ok: false,
      breaches: [
        { name: 'error_rate', detail: '9% of runs failed, over the 5% limit' },
      ],
      thresholds: { error_rate: 0.05 },
      unreadable: false,
    };

    it('is announced', async () => {
      answering(breached);
      render(<AlertBanner days={7} />);
      expect(await screen.findByRole('alert')).toBeInTheDocument();
    });

    it('carries the figure and the limit together', async () => {
      // "Errors are high" sends somebody to find out how high.
      answering(breached);
      render(<AlertBanner days={7} />);
      expect(
        await screen.findByText(/9% of runs failed, over the 5% limit/),
      ).toBeInTheDocument();
    });

    it('lists every one of them', async () => {
      answering({
        ...breached,
        breaches: [
          ...breached.breaches,
          { name: 'p95_seconds', detail: '95th percentile 289s, over the 60s limit' },
        ],
      });
      render(<AlertBanner days={7} />);
      expect(await screen.findByText(/289s/)).toBeInTheDocument();
    });
  });

  it('says nothing when the agent could not be asked', async () => {
    // Not "everything is fine": nobody checked.
    answering({ ...QUIET, unreadable: true });
    const { container } = render(<AlertBanner days={7} />);
    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });

  it('asks again when the window changes', async () => {
    const asked = answering(QUIET);
    const { rerender } = render(<AlertBanner days={7} />);
    await waitFor(() => expect(asked).toHaveBeenCalledWith(7));
    rerender(<AlertBanner days={30} />);
    await waitFor(() => expect(asked).toHaveBeenCalledWith(30));
  });
});

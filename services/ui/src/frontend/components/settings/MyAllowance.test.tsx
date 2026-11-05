import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { MyAllowance } from './MyAllowance';
import * as api from '../../services/allowance-api';

const CAPPED = {
  person: { spent: '1.25', limit: '5.00', remaining: '3.75', nearly_out: false },
  team: { spent: '8.00', limit: '20.00', remaining: '12.00', nearly_out: false },
  team_name: 'platform',
  unreadable: false,
};

describe('MyAllowance', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('says nothing while it is still asking', () => {
    vi.spyOn(api, 'readMyAllowance').mockReturnValue(new Promise(() => {}) as never);
    const { container } = render(<MyAllowance />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows what is left', async () => {
    vi.spyOn(api, 'readMyAllowance').mockResolvedValue(CAPPED as never);
    render(<MyAllowance />);
    expect(await screen.findByText(/3\.75 of 5\.00/)).toBeInTheDocument();
  });

  it('shows the team as well', async () => {
    vi.spyOn(api, 'readMyAllowance').mockResolvedValue(CAPPED as never);
    render(<MyAllowance />);
    expect(await screen.findByText(/platform/)).toBeInTheDocument();
  });

  it('shows nothing where nothing is capped', async () => {
    // A row reading "spent 1.25 of unlimited" is noise on
    // every page of every deployment that caps nothing.
    vi.spyOn(api, 'readMyAllowance').mockResolvedValue({
      person: { spent: '1.25', limit: null, remaining: null, nearly_out: false },
      team: null,
      team_name: null,
      unreadable: false,
    } as never);
    const { container } = render(<MyAllowance />);
    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });

  describe('nearly out', () => {
    it('warns before the refusal rather than with it', async () => {
      vi.spyOn(api, 'readMyAllowance').mockResolvedValue({
        ...CAPPED,
        person: { ...CAPPED.person, remaining: '0.40', nearly_out: true },
      } as never);
      render(<MyAllowance />);
      expect(await screen.findByRole('status')).toBeInTheDocument();
    });

    it('stays quiet with room to spare', async () => {
      vi.spyOn(api, 'readMyAllowance').mockResolvedValue(CAPPED as never);
      render(<MyAllowance />);
      await screen.findByText(/3\.75 of 5\.00/);
      expect(screen.queryByRole('status')).not.toBeInTheDocument();
    });
  });
});

describe('the month ahead', () => {
  const OVERRUNNING = {
    ...CAPPED,
    forecast: {
      person: {
        verdict: 'will-overrun',
        per_day: '6.00',
        projected_total: '186.00',
        remaining: '40.00',
        exhausted_on: '2026-03-16',
        spent: '60.00',
        limit: '100.00',
      },
      team: null,
    },
  };

  beforeEach(() => vi.restoreAllMocks());

  it('warns when the month is heading over', async () => {
    vi.spyOn(api, 'readMyAllowance').mockResolvedValue(OVERRUNNING as never);
    render(<MyAllowance />);
    expect(await screen.findByText(/2026-03-16/)).toBeInTheDocument();
  });

  it('names the daily burn, which is the thing to change', async () => {
    vi.spyOn(api, 'readMyAllowance').mockResolvedValue(OVERRUNNING as never);
    render(<MyAllowance />);
    expect(await screen.findByText(/6\.00/)).toBeInTheDocument();
  });

  it('says nothing about a month that is on track', async () => {
    // Said every month until the month it is not, it is a
    // row nobody is reading on the one that matters.
    vi.spyOn(api, 'readMyAllowance').mockResolvedValue({
      ...CAPPED,
      forecast: {
        person: {
          verdict: 'on-track',
          per_day: '1.00',
          projected_total: '31.00',
          remaining: '90.00',
          exhausted_on: null,
          spent: '10.00',
          limit: '100.00',
        },
        team: null,
      },
    } as never);
    render(<MyAllowance />);
    await screen.findByText(/3\.75 of 5\.00/);
    expect(screen.queryByTestId('month-ahead')).not.toBeInTheDocument();
  });

  it('still shows the daily allowance beside the warning', async () => {
    // The month is the new thing; it must not displace the
    // number that decides whether this task starts.
    vi.spyOn(api, 'readMyAllowance').mockResolvedValue(OVERRUNNING as never);
    render(<MyAllowance />);
    expect(await screen.findByText(/3\.75 of 5\.00/)).toBeInTheDocument();
  });

  it('says it plainly when the budget is already spent', async () => {
    vi.spyOn(api, 'readMyAllowance').mockResolvedValue({
      ...CAPPED,
      forecast: {
        person: {
          verdict: 'exhausted',
          per_day: '10.00',
          projected_total: '120.00',
          remaining: '0.00',
          exhausted_on: null,
          spent: '120.00',
          limit: '100.00',
        },
        team: null,
      },
    } as never);
    render(<MyAllowance />);
    expect(await screen.findByTestId('month-ahead')).toHaveTextContent(/100\.00/);
  });

  it('an agent that reports no month at all is not a warning', async () => {
    vi.spyOn(api, 'readMyAllowance').mockResolvedValue(CAPPED as never);
    render(<MyAllowance />);
    await screen.findByText(/3\.75 of 5\.00/);
    expect(screen.queryByTestId('month-ahead')).not.toBeInTheDocument();
  });
});

/**
 * What the month cost, per payer.
 *
 * Tokens answer "how much work was that". Nobody settles an
 * invoice in tokens and nobody allocates them to a team, so this
 * is money against a payer for a period — the shape somebody
 * copies into whatever they already use.
 *
 * The rate card version sits with the figure, because a number
 * with no version beside it cannot be checked against the
 * contract that priced it.
 */

import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { Chargeback } from './Chargeback';
import * as api from '../../services/chargeback-api';

const MONTH = {
  month: '2026-03',
  currency: 'USD',
  rate_card_version: 'v4',
  total: '430.75',
  rows: [
    { payer: 'platform', amount: '412.50', runs: 318 },
    { payer: 'alice', amount: '18.25', runs: 27 },
  ],
};

describe('Chargeback', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('says nothing while it is still asking', () => {
    vi.spyOn(api, 'readChargeback').mockReturnValue(new Promise(() => {}) as never);
    const { container } = render(<Chargeback />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows a row per payer', async () => {
    vi.spyOn(api, 'readChargeback').mockResolvedValue(MONTH as never);
    render(<Chargeback />);
    expect(await screen.findByText('platform')).toBeInTheDocument();
    expect(screen.getByText('alice')).toBeInTheDocument();
  });

  it('shows the money', async () => {
    vi.spyOn(api, 'readChargeback').mockResolvedValue(MONTH as never);
    render(<Chargeback />);
    expect(await screen.findByText(/412\.50/)).toBeInTheDocument();
  });

  it('shows how many runs made the figure', async () => {
    // A total with no count behind it cannot be checked.
    vi.spyOn(api, 'readChargeback').mockResolvedValue(MONTH as never);
    render(<Chargeback />);
    expect(await screen.findByText('318')).toBeInTheDocument();
  });

  it('shows the month it is for', async () => {
    vi.spyOn(api, 'readChargeback').mockResolvedValue(MONTH as never);
    render(<Chargeback />);
    expect(await screen.findByText(/2026-03/)).toBeInTheDocument();
  });

  it('shows which prices applied', async () => {
    vi.spyOn(api, 'readChargeback').mockResolvedValue(MONTH as never);
    render(<Chargeback />);
    expect(await screen.findByText(/v4/)).toBeInTheDocument();
  });

  it('shows the total', async () => {
    vi.spyOn(api, 'readChargeback').mockResolvedValue(MONTH as never);
    render(<Chargeback />);
    expect(await screen.findByText(/430\.75/)).toBeInTheDocument();
  });

  it('says a month with nothing in it was quiet, rather than showing an empty table', async () => {
    // An empty table reads as something failing to load.
    vi.spyOn(api, 'readChargeback').mockResolvedValue({
      ...MONTH,
      rows: [],
      total: '0.00',
    } as never);
    render(<Chargeback />);
    expect(await screen.findByRole('status')).toBeInTheDocument();
  });

  it('shows nothing at all when the agent cannot answer', async () => {
    // An older agent that has never been asked is not a month
    // in which nobody spent anything.
    vi.spyOn(api, 'readChargeback').mockResolvedValue(null);
    const { container } = render(<Chargeback />);
    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });
});

describe('it is actually on the page', () => {
  it('the usage page mounts it', async () => {
    // A panel nobody mounts shows nobody anything.
    const source = await import('../../pages/AnalyticsPage?raw');
    expect(String(source.default)).toContain('<Chargeback');
  });
});

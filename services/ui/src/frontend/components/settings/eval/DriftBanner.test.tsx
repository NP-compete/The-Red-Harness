import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { DriftBanner } from './DriftBanner';

const answer = vi.hoisted(() => ({
  body: {
    movement: 'steady' as string,
    gap: 0,
    outliers: [] as string[],
    needs_attention: false,
  },
  ok: true,
}));

beforeEach(() => {
  answer.body = { movement: 'steady', gap: 0, outliers: [], needs_attention: false };
  answer.ok = true;
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation(() =>
      Promise.resolve({ ok: answer.ok, json: () => Promise.resolve(answer.body) }),
    ),
  );
});

describe('DriftBanner', () => {
  it('says when scores are holding', async () => {
    render(<DriftBanner />);
    expect(await screen.findByText('Scores are holding steady')).toBeInTheDocument();
  });

  it('says when scores are falling', async () => {
    answer.body = { movement: 'falling', gap: -0.12, outliers: [], needs_attention: true };
    render(<DriftBanner />);
    expect(await screen.findByText('Scores are falling')).toBeInTheDocument();
  });

  it('says how far from the baseline things sit', async () => {
    answer.body = { movement: 'falling', gap: -0.12, outliers: [], needs_attention: true };
    render(<DriftBanner />);
    expect(await screen.findByText('12 points below baseline')).toBeInTheDocument();
  });

  it('names a run that sat apart from the rest', async () => {
    answer.body = { movement: 'steady', gap: 0, outliers: ['r2'], needs_attention: false };
    render(<DriftBanner />);
    expect(await screen.findByText('1 run sat well outside the rest: r2')).toBeInTheDocument();
  });

  it('admits when there is not enough history', async () => {
    answer.body = { movement: 'unknown', gap: 0, outliers: [], needs_attention: false };
    render(<DriftBanner />);
    expect(await screen.findByText('Not enough runs to tell')).toBeInTheDocument();
  });

  it('says nothing at all when the agent cannot answer', async () => {
    answer.ok = false;
    const { container } = render(<DriftBanner />);
    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });

  it('asks the agent for the drift reading', async () => {
    render(<DriftBanner />);
    await screen.findByText('Scores are holding steady');
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/evals/drift'),
      expect.anything(),
    );
  });
});

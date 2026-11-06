import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ErrorBudgetCard } from './ErrorBudgetCard';

const answer = vi.hoisted(() => ({
  ok: true,
  body: {
    state: 'healthy' as string,
    used: 0.2,
    failures_left: 8,
    may_deploy: true,
    warn: false,
    exceptional: false,
    reason: '',
  },
}));

beforeEach(() => {
  answer.ok = true;
  answer.body = {
    state: 'healthy',
    used: 0.2,
    failures_left: 8,
    may_deploy: true,
    warn: false,
    exceptional: false,
    reason: '',
  };
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation(() =>
      Promise.resolve({ ok: answer.ok, json: () => Promise.resolve(answer.body) }),
    ),
  );
});

describe('ErrorBudgetCard', () => {
  it('says the budget is holding', async () => {
    render(<ErrorBudgetCard />);
    expect(await screen.findByText(/error budget/i)).toBeInTheDocument();
  });

  it('says how many failures are left', async () => {
    render(<ErrorBudgetCard />);
    expect(
      await screen.findByText('8 more failures before changes pause'),
    ).toBeInTheDocument();
  });

  it('counts down what is left rather than up what is gone', async () => {
    answer.body = { ...answer.body, state: 'at-risk', used: 0.85, failures_left: 1, warn: true };
    render(<ErrorBudgetCard />);
    expect(await screen.findByText('15% of the error budget left')).toBeInTheDocument();
  });

  it('is blunt when the budget is spent', async () => {
    answer.body = {
      ...answer.body,
      state: 'exhausted',
      used: 1,
      failures_left: 0,
      may_deploy: false,
      reason: 'the error budget is spent',
    };
    render(<ErrorBudgetCard />);
    expect(await screen.findByText('the error budget is spent')).toBeInTheDocument();
  });

  it('admits when there is not enough history', async () => {
    answer.body = { ...answer.body, state: 'unknown', used: 0, failures_left: 0 };
    render(<ErrorBudgetCard />);
    expect(await screen.findByText('Not enough history yet')).toBeInTheDocument();
  });

  it('says nothing at all when the agent cannot answer', async () => {
    answer.ok = false;
    const { container } = render(<ErrorBudgetCard />);
    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });

  it('asks the agent over the window it was given', async () => {
    render(<ErrorBudgetCard days={30} />);
    await screen.findByText(/error budget/i);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('days=30'),
      expect.anything(),
    );
  });
});

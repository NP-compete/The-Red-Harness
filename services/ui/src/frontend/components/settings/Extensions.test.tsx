import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { Extensions } from './Extensions';

const api = vi.hoisted(() => ({ listExtensions: vi.fn() }));
vi.mock('../../services/extensions-api', () => api);

const LOADED = { path: 'house.style:Redactor', required: true, loaded: true, problem: '' };
const BROKEN = { path: 'gone:Thing', required: false, loaded: false, problem: 'gone: no module named gone' };

beforeEach(() => api.listExtensions.mockResolvedValue([LOADED]));
afterEach(() => vi.clearAllMocks());

describe('Extensions', () => {
  it('names what is interposed', async () => {
    render(<Extensions />);
    expect(await screen.findByText('house.style:Redactor')).toBeInTheDocument();
  });

  it('says it is in the path', async () => {
    render(<Extensions />);
    expect(await screen.findByText(/in the path/i)).toBeInTheDocument();
  });

  it('says a run will not proceed without a required one', async () => {
    render(<Extensions />);
    expect(await screen.findByText(/required/i)).toBeInTheDocument();
  });

  it('says when one is not loaded, and why', async () => {
    api.listExtensions.mockResolvedValue([BROKEN]);
    render(<Extensions />);
    expect(await screen.findByText(/no module named gone/)).toBeInTheDocument();
  });

  it('says plainly when a deployment interposes nothing', async () => {
    api.listExtensions.mockResolvedValue([]);
    render(<Extensions />);
    expect(await screen.findByText(/nothing is interposed|no extensions/i)).toBeInTheDocument();
  });

  it('says nothing at all when the question cannot be asked', async () => {
    api.listExtensions.mockResolvedValue(null);
    const { container } = render(<Extensions />);
    await waitFor(() => expect(api.listExtensions).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });
});

describe('what an extension costs', () => {
  const TIMED = {
    ...LOADED,
    timing: { calls: 12, refusals: 0, refusal_rate: 0, average_ms: 210, slowest_ms: 980 },
  };

  it('says how long it usually takes', async () => {
    api.listExtensions.mockResolvedValue([TIMED]);
    render(<Extensions />);
    expect(await screen.findByText(/210 ms/)).toBeInTheDocument();
  });

  it('says how slow it has been at worst', async () => {
    api.listExtensions.mockResolvedValue([TIMED]);
    render(<Extensions />);
    expect(await screen.findByText(/980 ms/)).toBeInTheDocument();
  });

  it('says how often it refuses when it does', async () => {
    api.listExtensions.mockResolvedValue([
      { ...TIMED, timing: { ...TIMED.timing, refusals: 3, refusal_rate: 0.25 } },
    ]);
    render(<Extensions />);
    expect(await screen.findByText(/25%/)).toBeInTheDocument();
  });

  it('says nothing about cost for one that has never run', async () => {
    api.listExtensions.mockResolvedValue([{ ...LOADED, timing: null }]);
    render(<Extensions />);
    await screen.findByText('house.style:Redactor');
    expect(screen.queryByText(/ms typical/)).not.toBeInTheDocument();
  });

  it('still shows a broken extension, with no figures to show', async () => {
    api.listExtensions.mockResolvedValue([{ ...BROKEN, timing: null }]);
    render(<Extensions />);
    expect(await screen.findByText(/no module named gone/)).toBeInTheDocument();
  });
});

import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ModelPrices } from './ModelPrices';

function answers(body: unknown, ok = true) {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok, status: ok ? 200 : 503, json: async () => body }));
}

const CARD = {
  version: '2026-10',
  currency: 'USD',
  source: 'config/agent/runtime/rates.yaml',
  problem: '',
  rates: [{ model: 'gemini-3.8-flash', input_per_1k: '0.00015', output_per_1k: '0.0006' }],
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('ModelPrices', () => {
  it('names a priced model', async () => {
    answers(CARD);
    render(<ModelPrices />);
    expect(await screen.findByText('gemini-3.8-flash')).toBeInTheDocument();
  });

  it('says what a thousand tokens in costs', async () => {
    answers(CARD);
    render(<ModelPrices />);
    expect(await screen.findByText(/0\.00015/)).toBeInTheDocument();
  });

  it('says what a thousand tokens out costs', async () => {
    answers(CARD);
    render(<ModelPrices />);
    expect(await screen.findByText(/0\.0006/)).toBeInTheDocument();
  });

  it('says which version of the prices is in force', async () => {
    answers(CARD);
    render(<ModelPrices />);
    expect(await screen.findByText(/2026-10/)).toBeInTheDocument();
  });

  it('says plainly when nothing is priced', async () => {
    answers({ ...CARD, version: 'none', rates: [] });
    render(<ModelPrices />);
    expect(await screen.findByText(/no (model )?prices/i)).toBeInTheDocument();
  });

  it('says where to put prices when there are none', async () => {
    answers({ ...CARD, version: 'none', rates: [] });
    render(<ModelPrices />);
    expect(await screen.findByText(/config\/agent\/runtime\/rates\.yaml/)).toBeInTheDocument();
  });

  it('does not call an unpriced deployment free', async () => {
    answers({ ...CARD, version: 'none', rates: [] });
    render(<ModelPrices />);
    await screen.findByText(/no (model )?prices/i);
    expect(screen.queryByText(/\$0\.00|free/i)).not.toBeInTheDocument();
  });

  it('reports a price list it could not read', async () => {
    answers({ ...CARD, rates: [], problem: 'rates.yaml must say which version it holds' });
    render(<ModelPrices />);
    expect(await screen.findByText(/must say which version/)).toBeInTheDocument();
  });

  it('says nothing at all when the agent cannot be reached', async () => {
    answers({}, false);
    const { container } = render(<ModelPrices />);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(container).toBeEmptyDOMElement();
  });
});

describe('what a run may spend', () => {
  it('says the ceiling a deployment set', async () => {
    answers({ ...CARD, run_limit: '0.05', run_warn_at: '0.01' });
    render(<ModelPrices />);
    expect(await screen.findByText(/stop at .*0\.05/i)).toBeInTheDocument();
  });

  it('says where it will warn first', async () => {
    answers({ ...CARD, run_limit: '0.05', run_warn_at: '0.01' });
    render(<ModelPrices />);
    expect(await screen.findByText(/0\.01/)).toBeInTheDocument();
  });

  it('says nothing caps a run when nothing does', async () => {
    answers(CARD);
    render(<ModelPrices />);
    await screen.findByText('gemini-3.8-flash');
    expect(screen.queryByText(/stop at/i)).not.toBeInTheDocument();
  });

  it('mentions the ceiling even where no prices are set', async () => {
    // The ceiling is unreachable without prices, and saying so is
    // the difference between "no limit" and "a limit that cannot fire".
    answers({ ...CARD, version: 'none', rates: [], run_limit: '0.05' });
    render(<ModelPrices />);
    expect(await screen.findByText(/0\.05/)).toBeInTheDocument();
  });
});

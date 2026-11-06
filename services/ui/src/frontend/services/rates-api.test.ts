import { afterEach, describe, expect, it, vi } from 'vitest';

import { getModelPrices, priceTokens } from './rates-api';

function answers(status: number, body: unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: status >= 200 && status < 300,
      status,
      json: async () => body,
    }),
  );
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

describe('getModelPrices', () => {
  it('says which version of the prices is in force', async () => {
    answers(200, CARD);
    expect((await getModelPrices())?.version).toBe('2026-10');
  });

  it('lists a model and what it costs', async () => {
    answers(200, CARD);
    expect((await getModelPrices())?.rates[0]).toEqual({
      model: 'gemini-3.8-flash',
      inputPer1k: '0.00015',
      outputPer1k: '0.0006',
    });
  });

  it('says where prices would be read from', async () => {
    answers(200, CARD);
    expect((await getModelPrices())?.source).toBe('config/agent/runtime/rates.yaml');
  });

  it('passes on a price list that could not be read', async () => {
    answers(200, { ...CARD, rates: [], problem: 'rates.yaml must say which version' });
    expect((await getModelPrices())?.problem).toMatch(/version/);
  });

  it('treats a deployment with no prices as no prices, not an error', async () => {
    answers(200, { version: 'none', currency: 'USD', source: 'x', problem: '', rates: [] });
    expect((await getModelPrices())?.rates).toEqual([]);
  });

  it('says nothing when the agent cannot be reached', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
    expect(await getModelPrices()).toBeNull();
  });

  it('says nothing when the agent refuses', async () => {
    answers(404, {});
    expect(await getModelPrices()).toBeNull();
  });
});

describe('priceTokens', () => {
  it('says what counts of its own come to', async () => {
    answers(200, { cost: '0.0009', currency: 'USD', rate_card_version: '2026-10', unpriced: [] });
    expect((await priceTokens(2000, 1000))?.cost).toBe('0.0009');
  });

  it('passes on a count nothing could price', async () => {
    answers(200, { cost: null, currency: 'USD', rate_card_version: 'none', unpriced: ['m'] });
    expect((await priceTokens(10, 10))?.cost).toBeNull();
  });

  it('says nothing when the agent cannot be reached', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
    expect(await priceTokens(10, 10)).toBeNull();
  });

  it('does not ask about a conversation that has used nothing', async () => {
    const fetched = vi.fn();
    vi.stubGlobal('fetch', fetched);
    expect(await priceTokens(0, 0)).toBeNull();
    expect(fetched).not.toHaveBeenCalled();
  });
});

describe('what a run may spend', () => {
  it('reports the ceiling a deployment set', async () => {
    answers(200, { ...CARD, run_limit: '0.05', run_warn_at: '0.01' });
    expect((await getModelPrices())?.runLimit).toBe('0.05');
  });

  it('reports the point it will warn at', async () => {
    answers(200, { ...CARD, run_limit: '0.05', run_warn_at: '0.01' });
    expect((await getModelPrices())?.runWarnAt).toBe('0.01');
  });

  it('reports no ceiling as none rather than as zero', async () => {
    answers(200, CARD);
    expect((await getModelPrices())?.runLimit).toBe('');
  });
});

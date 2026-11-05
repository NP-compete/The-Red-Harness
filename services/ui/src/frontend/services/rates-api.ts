import { buildAgentApiUrl } from '../lib/app-paths';
import { authenticatedFetch } from './authenticated-fetch';

export interface ModelPrice {
  model: string;
  inputPer1k: string;
  outputPer1k: string;
}

export interface ModelPrices {
  version: string;
  currency: string;
  /** Where the agent looks for prices, so "none" is something to fix. */
  source: string;
  /** Why there are no prices, when the file was there but unreadable. */
  problem: string;
  /** What one run may spend, or '' when nothing caps it. */
  runLimit: string;
  /** Where it will say something first, or '' when it will not. */
  runWarnAt: string;
  rates: ModelPrice[];
}

export interface PricedTokens {
  cost: string | null;
  currency: string;
}

/**
 * What a count of tokens comes to, for a caller holding its own tally.
 *
 * A deployment that stores no running total still shows the turns on
 * screen, and those turns cost money whether or not anything recorded
 * the figure.
 */
export async function priceTokens(
  inputTokens: number,
  outputTokens: number,
): Promise<PricedTokens | null> {
  if (inputTokens <= 0 && outputTokens <= 0) return null;
  try {
    const response = await authenticatedFetch(
      buildAgentApiUrl(
        `/rates/price?input_tokens=${inputTokens}&output_tokens=${outputTokens}`,
      ),
      { method: 'GET' },
    );
    if (!response.ok) return null;
    const body = (await response.json()) as { cost?: string | null; currency?: string };
    return { cost: body.cost ?? null, currency: body.currency ?? 'USD' };
  } catch {
    return null;
  }
}

/**
 * The prices this deployment charges model calls at.
 *
 * A cost shown without the price behind it is a number to be taken on
 * faith. This is how someone checks it.
 */
export async function getModelPrices(): Promise<ModelPrices | null> {
  try {
    const response = await authenticatedFetch(buildAgentApiUrl('/rates'), { method: 'GET' });
    if (!response.ok) return null;
    const body = (await response.json()) as {
      version?: string;
      currency?: string;
      source?: string;
      problem?: string;
      run_limit?: string;
      run_warn_at?: string;
      rates?: Array<{ model?: string; input_per_1k?: string; output_per_1k?: string }>;
    };
    return {
      version: body.version ?? 'none',
      currency: body.currency ?? 'USD',
      source: body.source ?? '',
      problem: body.problem ?? '',
      runLimit: body.run_limit ?? '',
      runWarnAt: body.run_warn_at ?? '',
      rates: (body.rates ?? []).map((rate) => ({
        model: rate.model ?? '',
        inputPer1k: rate.input_per_1k ?? '0',
        outputPer1k: rate.output_per_1k ?? '0',
      })),
    };
  } catch {
    return null;
  }
}

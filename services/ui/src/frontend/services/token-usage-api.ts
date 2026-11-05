import { buildAgentApiUrl } from '../lib/app-paths';
import { authenticatedFetch } from './authenticated-fetch';

export interface ThreadTokenUsage {
  used: number;
  inputTokens: number;
  outputTokens: number;
  /** What those tokens came to, or null when nothing priced them. */
  cost?: string | null;
  currency?: string;
}

/**
 * What this conversation has cost in tokens, or `null` when there is
 * nothing to report.
 *
 * Tracking is off by default and a thread may have no record yet;
 * neither is an error worth putting in front of anyone.
 */
export async function getThreadTokenUsage(
  threadId: string,
): Promise<ThreadTokenUsage | null> {
  try {
    const response = await authenticatedFetch(
      buildAgentApiUrl(`/threads/${threadId}/token-usage`),
      { method: 'GET' },
    );
    if (!response.ok) return null;
    const body = (await response.json()) as {
      used?: number;
      input_tokens?: number;
      output_tokens?: number;
      cost?: string | null;
      currency?: string;
    };
    return {
      used: body.used ?? 0,
      inputTokens: body.input_tokens ?? 0,
      outputTokens: body.output_tokens ?? 0,
      cost: body.cost ?? null,
      currency: body.currency ?? 'USD',
    };
  } catch {
    return null;
  }
}

import { buildAgentApiUrl } from '../lib/app-paths';
import { authenticatedFetch } from './authenticated-fetch';
import type { SystemStatus } from '../lib/system-health';

/**
 * The parts the agent depends on, and whether each is answering.
 *
 * The header already says whether the agent is up. What it cannot
 * say is which piece is down when it is not — and that is the first
 * question an operator has.
 */
export async function getSystemHealth(): Promise<SystemStatus[] | null> {
  try {
    const response = await authenticatedFetch(buildAgentApiUrl('/health'), {
      method: 'GET',
    });
    if (!response.ok) return null;

    const body = (await response.json()) as Record<string, unknown>;
    return Object.entries(body)
      // `status` is the verdict on everything below it, not a part.
      .filter(([key, value]) => key !== 'status' && typeof value === 'string')
      .map(([key, value]) => ({
        name: key.replace(/_/g, ' '),
        state: value === 'connected' ? ('connected' as const) : ('degraded' as const),
      }));
  } catch {
    return null;
  }
}

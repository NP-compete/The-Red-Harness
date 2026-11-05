import { buildAgentApiUrl } from '../lib/app-paths';
import { authenticatedFetch } from './authenticated-fetch';

export interface DedupeResult {
  removed: number;
  remaining: number;
}

/**
 * Collapse memories that say the same thing twice.
 *
 * The agent writes a fact each time it learns one, so the same
 * preference arrives in slightly different words over a few
 * conversations. The list shows every copy and leaves the reader to
 * spot them; this keeps the fullest wording of each and drops the
 * rest.
 */
export async function removeDuplicateMemories(): Promise<DedupeResult | null> {
  try {
    const response = await authenticatedFetch(
      buildAgentApiUrl('/personalization/memories/deduplicate'),
      { method: 'POST' },
    );
    if (!response.ok) return null;

    const body = (await response.json()) as { removed?: unknown; remaining?: unknown };
    if (typeof body.removed !== 'number' || typeof body.remaining !== 'number') {
      return null;
    }
    return { removed: body.removed, remaining: body.remaining };
  } catch {
    return null;
  }
}

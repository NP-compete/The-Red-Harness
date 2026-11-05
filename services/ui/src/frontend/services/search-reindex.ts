import { buildAgentApiUrl } from '../lib/app-paths';
import { authenticatedFetch } from './authenticated-fetch';

/**
 * Rebuild the search index for this account.
 *
 * The read path reindexes on its own; this exists for the case where
 * someone needs to rule the index out as the problem. Returns how many
 * conversations were indexed, or `null` if it could not be done.
 */
export async function reindexThreads(): Promise<number | null> {
  try {
    const response = await authenticatedFetch(buildAgentApiUrl('/search/reindex'), {
      method: 'POST',
    });
    if (!response.ok) return null;
    const body = (await response.json()) as { indexed?: number };
    return body.indexed ?? 0;
  } catch {
    return null;
  }
}

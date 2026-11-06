import type { ExtensionTiming } from '../lib/extension-cost';
import { buildAgentApiUrl } from '../lib/app-paths';
import { authenticatedFetch } from './authenticated-fetch';

export interface Extension {
  path: string;
  /** The run is refused without it. */
  required: boolean;
  loaded: boolean;
  /** Why it is not loaded, when it is not. */
  problem: string;
  /** What it has cost so far, or null if it has never run. */
  timing: ExtensionTiming | null;
}

/**
 * What this deployment has interposed on its runs.
 *
 * `null` means the question could not be asked. An empty list means
 * nothing is interposed, which is a different answer and the
 * ordinary one.
 */
export async function listExtensions(): Promise<Extension[] | null> {
  try {
    const response = await authenticatedFetch(buildAgentApiUrl('/extensions'), {
      method: 'GET',
    });
    if (!response.ok) return null;
    const body = (await response.json()) as { extensions?: Extension[] };
    return body.extensions ?? [];
  } catch {
    return null;
  }
}

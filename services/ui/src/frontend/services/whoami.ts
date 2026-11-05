import { buildAgentApiUrl } from '../lib/app-paths';
import { authenticatedFetch } from './authenticated-fetch';

export interface Whoami {
  userId: string;
  role: string;
  isDeveloper: boolean;
}

/**
 * Who the agent takes this caller to be.
 *
 * The page otherwise works it out from whether sign-in is switched
 * on, which is a guess. This is the same answer the agent will
 * enforce when an operator surface is asked for, so it is the one
 * worth showing a reader.
 *
 * `null` means not knowing — unreachable, or an answer with nothing
 * in it. Nothing is assumed from that either way.
 */
export async function getWhoami(): Promise<Whoami | null> {
  try {
    const response = await authenticatedFetch(buildAgentApiUrl('/auth/whoami'), {
      method: 'GET',
    });
    if (!response.ok) return null;

    const body = (await response.json()) as {
      user_id?: string;
      role?: string;
      is_developer?: boolean;
    };
    if (!body.role) return null;

    return {
      userId: body.user_id ?? '',
      role: body.role,
      isDeveloper: body.is_developer === true,
    };
  } catch {
    return null;
  }
}

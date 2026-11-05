import { buildAgentApiUrl } from '../lib/app-paths';
import { authenticatedFetch } from './authenticated-fetch';

export type ShareScope = 'authenticated' | 'public';

export interface Share {
  shareId: string;
  /** Which conversation it publishes, and what it is called. */
  threadId?: string;
  title?: string;
  scope: ShareScope;
  active: boolean;
  views: number;
  expiresAt: string | null;
  path: string;
}

interface ShareResponse {
  shared?: boolean;
  share_id?: string;
  thread_id?: string;
  title?: string;
  scope?: string;
  active?: boolean;
  views?: number;
  expires_at?: string | null;
  path?: string;
}

function asShare(body: ShareResponse): Share | null {
  if (!body.share_id) return null;
  return {
    shareId: body.share_id,
    threadId: body.thread_id,
    title: body.title,
    scope: body.scope === 'public' ? 'public' : 'authenticated',
    active: body.active !== false,
    views: body.views ?? 0,
    expiresAt: body.expires_at ?? null,
    path: body.path ?? `/shared/${body.share_id}`,
  };
}

/** The share on this conversation, or `null` when there is none to report. */
export async function getShare(threadId: string): Promise<Share | null> {
  try {
    const response = await authenticatedFetch(
      buildAgentApiUrl(`/threads/${threadId}/share`),
      { method: 'GET' },
    );
    if (!response.ok) return null;
    return asShare((await response.json()) as ShareResponse);
  } catch {
    // Not knowing is reported as no share rather than a wrong one.
    return null;
  }
}

export async function createShare(
  threadId: string,
  scope: ShareScope,
  expiryDays: number,
): Promise<Share | null> {
  try {
    const response = await authenticatedFetch(
      buildAgentApiUrl(`/threads/${threadId}/share`),
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scope, expiry_days: expiryDays }),
      },
    );
    if (!response.ok) return null;
    return asShare((await response.json()) as ShareResponse);
  } catch {
    return null;
  }
}

export async function revokeShare(threadId: string): Promise<boolean> {
  try {
    const response = await authenticatedFetch(
      buildAgentApiUrl(`/threads/${threadId}/share`),
      { method: 'DELETE' },
    );
    if (!response.ok) return false;
    return ((await response.json()) as { revoked?: boolean }).revoked === true;
  } catch {
    return false;
  }
}


/**
 * Every link this account has published.
 *
 * Without this the only way to find out what you have shared is to
 * remember, so an empty answer is reported as nothing shared rather
 * than as a failure.
 */
export async function listShares(): Promise<Share[]> {
  try {
    const response = await authenticatedFetch(buildAgentApiUrl('/shares'), {
      method: 'GET',
    });
    if (!response.ok) return [];
    const body = (await response.json()) as { shares?: ShareResponse[] };
    return (body.shares ?? [])
      .map(asShare)
      .filter((share): share is Share => share !== null);
  } catch {
    return [];
  }
}

import { buildAgentApiUrl } from '../lib/app-paths';
import { authenticatedFetch } from './authenticated-fetch';
import type { FeatureFact } from '../lib/feature-view';

export interface FeatureReport {
  features: FeatureFact[];
  /** The declarations exist but could not be read. */
  unreadable: boolean;
}

/**
 * The optional capabilities and whether each is on.
 *
 * A request that fails is reported as unreadable rather than as an
 * empty list: "this deployment has no optional capabilities" and
 * "nobody could tell you" look identical on screen and are not the
 * same thing at all.
 */
export async function readFeatures(): Promise<FeatureReport> {
  try {
    const response = await authenticatedFetch(buildAgentApiUrl('/features'), {
      method: 'GET',
    });
    if (!response.ok) return { features: [], unreadable: true };
    const body = (await response.json()) as Partial<FeatureReport>;
    return {
      features: Array.isArray(body.features) ? body.features : [],
      unreadable: Boolean(body.unreadable),
    };
  } catch {
    return { features: [], unreadable: true };
  }
}

export interface WriteResult {
  ok: boolean;
  /** What the agent said when it refused. */
  reason?: string;
}

/**
 * Ask the agent to turn one capability on or off.
 *
 * The rules are the agent's — who may set a flag, and what it needs
 * first. This reports the refusal rather than interpreting it: the
 * sentence the agent gives is the only thing that explains a switch
 * that snaps back.
 */
export async function writeFeature(key: string, enabled: boolean): Promise<WriteResult> {
  try {
    const response = await authenticatedFetch(
      buildAgentApiUrl(`/features/${encodeURIComponent(key)}`),
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      },
    );
    if (response.ok) return { ok: true };
    const body = (await response.json().catch(() => ({}))) as { detail?: string };
    return { ok: false, reason: body.detail };
  } catch {
    return { ok: false };
  }
}

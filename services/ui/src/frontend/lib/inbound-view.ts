/**
 * Whether another system may call this agent, and on what terms.
 *
 * The limits matter more than the door. An open door with nothing
 * behind it is one caller away from spending the deployment's
 * budget, and nothing else on this page would show that.
 */

export interface InboundReport {
  enabled: boolean;
  auth_mode: string;
  published_tools: number;
  limits: {
    per_second: number;
    burst: number;
    /** A string, because it is money. */
    daily_spend: string | null;
  } | null;
}

export interface InboundDescription {
  open: boolean;
  authMode: string;
  publishedTools: number;
  rate: string | null;
  dailySpend: string | null;
  /** Open, and nothing stops one caller taking all of it. */
  unlimited: boolean;
}

export function describeInbound(
  found: InboundReport | null,
): InboundDescription | null {
  if (!found || typeof found.enabled !== 'boolean') return null;

  const limits = found.limits;
  return {
    open: found.enabled,
    authMode: found.auth_mode || '',
    publishedTools: found.published_tools ?? 0,
    rate: limits ? `${limits.per_second}/s, burst ${limits.burst}` : null,
    dailySpend: limits?.daily_spend ?? null,
    // A rate limit alone does not count: it catches a caller going
    // too fast, not one going at exactly the agreed rate and
    // spending the month's budget by Thursday.
    unlimited: found.enabled && !limits?.daily_spend,
  };
}

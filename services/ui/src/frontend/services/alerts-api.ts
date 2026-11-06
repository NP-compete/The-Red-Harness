import { buildAgentApiUrl } from '../lib/app-paths';

export interface Breach {
  name: string;
  detail: string;
}

export interface AlertReport {
  ok: boolean;
  breaches: Breach[];
  thresholds: Record<string, unknown>;
  /** Nobody could be asked — not the same as nothing being wrong. */
  unreadable: boolean;
}

const UNASKED: AlertReport = {
  ok: true,
  breaches: [],
  thresholds: {},
  unreadable: true,
};

/**
 * Anything over a configured limit.
 *
 * A failure is reported as unreadable rather than as healthy.
 * "Nothing is wrong" and "nobody checked" render identically and
 * are not the same thing — and only one of them is safe to act
 * on.
 */
export async function readAlerts(days: number): Promise<AlertReport> {
  try {
    const response = await fetch(buildAgentApiUrl(`/analytics/alerts?days=${days}`));
    if (!response.ok) return UNASKED;
    const body = (await response.json()) as Partial<AlertReport>;
    if (typeof body.ok !== 'boolean') return UNASKED;
    return {
      ok: body.ok,
      breaches: Array.isArray(body.breaches) ? body.breaches : [],
      thresholds: body.thresholds ?? {},
      unreadable: false,
    };
  } catch {
    return UNASKED;
  }
}

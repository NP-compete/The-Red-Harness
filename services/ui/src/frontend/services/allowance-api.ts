import { buildAppPath } from '../lib/app-paths';
import type { AllowanceReport } from '../lib/allowance-view';

/**
 * What this person has spent today and what they may spend.
 *
 * `null` on anything other than a clean answer — an older
 * agent that has never been asked is not a person with no
 * allowance.
 */
export async function readMyAllowance(): Promise<AllowanceReport | null> {
  try {
    const response = await fetch(buildAppPath('/api/proxy/agent/limits/mine'), {
      credentials: 'include',
    });
    if (!response.ok) return null;
    const body = (await response.json()) as Partial<AllowanceReport>;
    return typeof body.person?.spent === 'string' ? (body as AllowanceReport) : null;
  } catch {
    return null;
  }
}

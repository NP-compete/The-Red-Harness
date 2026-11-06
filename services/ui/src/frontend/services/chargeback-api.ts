import { buildAppPath } from '../lib/app-paths';

export interface ChargebackRow {
  payer: string;
  amount: string;
  runs: number;
}

export interface ChargebackReport {
  month: string;
  currency: string;
  rate_card_version: string;
  total: string;
  rows: ChargebackRow[];
}

/**
 * What a month cost, per payer.
 *
 * `null` on anything other than a clean answer — an older agent
 * that has never been asked is not a month in which nobody
 * spent anything, and showing one as the other is how a wrong
 * invoice goes out.
 */
export async function readChargeback(
  month = '',
): Promise<ChargebackReport | null> {
  const query = month ? `?month=${encodeURIComponent(month)}` : '';
  try {
    const response = await fetch(
      buildAppPath(`/api/proxy/agent/costs/chargeback${query}`),
      { credentials: 'include' },
    );
    if (!response.ok) return null;
    const body = (await response.json()) as Partial<ChargebackReport>;
    return Array.isArray(body.rows) ? (body as ChargebackReport) : null;
  } catch {
    return null;
  }
}

import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import {
  readChargeback,
  type ChargebackReport,
} from '../../services/chargeback-api';

/**
 * What the month cost, per payer.
 *
 * Tokens answer "how much work was that". Nobody settles an
 * invoice in tokens and nobody allocates them to a team, so
 * this is money against a payer for a period — the shape
 * somebody copies into whatever they already use.
 *
 * The rate card version sits beside the figures. A number with
 * no version against it cannot be checked against the contract
 * that priced it, and re-pricing history so that it checks out
 * is how a record stops being a record.
 */
export function Chargeback() {
  const { t } = useTranslation();
  const [report, setReport] = useState<ChargebackReport | null | undefined>(
    undefined,
  );

  useEffect(() => {
    let live = true;
    void readChargeback().then((found) => {
      if (live) setReport(found);
    });
    return () => {
      live = false;
    };
  }, []);

  // Undefined is still asking; null is an agent that cannot
  // answer, which is not a month in which nobody spent
  // anything.
  if (report === undefined || report === null) return null;

  return (
    <section className="mb-12">
      <h2 className="mb-2 text-base font-semibold">{t('chargeback.heading')}</h2>
      <p className="mb-5 text-xs leading-relaxed text-muted-foreground">
        {t('chargeback.note', {
          month: report.month,
          version: report.rate_card_version,
        })}
      </p>

      {report.rows.length === 0 ? (
        // Said rather than shown as an empty table, which
        // reads as something failing to load.
        <p role="status" className="text-sm text-muted-foreground">
          {t('chargeback.quiet', { month: report.month })}
        </p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-muted-foreground">
              <th className="pb-2 font-normal">{t('chargeback.payer')}</th>
              <th className="pb-2 text-right font-normal">
                {t('chargeback.amount', { currency: report.currency })}
              </th>
              <th className="pb-2 text-right font-normal">{t('chargeback.runs')}</th>
            </tr>
          </thead>
          <tbody>
            {report.rows.map((row) => (
              <tr key={row.payer} className="border-t border-border">
                <td className="py-2">{row.payer}</td>
                <td className="py-2 text-right tabular-nums">{row.amount}</td>
                <td className="py-2 text-right tabular-nums text-muted-foreground">
                  {row.runs}
                </td>
              </tr>
            ))}
            <tr className="border-t border-border font-medium">
              <td className="py-2">{t('chargeback.total')}</td>
              <td className="py-2 text-right tabular-nums">{report.total}</td>
              <td />
            </tr>
          </tbody>
        </table>
      )}
    </section>
  );
}

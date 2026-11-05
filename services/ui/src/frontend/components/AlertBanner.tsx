import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle } from 'lucide-react';

import { readAlerts, type AlertReport } from '../services/alerts-api';

/**
 * What is over a limit, said where somebody is already looking.
 *
 * Shown only when something is. A banner on every healthy window
 * is a banner people stop reading, and then the one that mattered
 * goes unread with the rest.
 */
export function AlertBanner({ days }: { days: number }) {
  const { t } = useTranslation();
  const [report, setReport] = useState<AlertReport | null>(null);

  useEffect(() => {
    let live = true;
    setReport(null);
    void readAlerts(days).then((found) => {
      if (live) setReport(found);
    });
    return () => {
      live = false;
    };
  }, [days]);

  // Silent in three cases, and only one of them is "all well":
  // still asking, nobody could be asked, and nothing over a line.
  if (!report || report.unreadable || report.breaches.length === 0) {
    return null;
  }

  return (
    <div
      role="alert"
      className="mb-6 rounded-lg border border-amber-500/40 bg-amber-500/5 p-3"
    >
      <div className="flex items-start gap-2">
        <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-500" aria-hidden="true" />
        <div>
          <p className="text-sm font-medium text-foreground">{t('alerts.headline')}</p>
          <ul className="mt-1 list-none space-y-0.5">
            {report.breaches.map((breach) => (
              <li key={breach.name} className="text-xs text-amber-500/90">
                {/* The figure and the limit together: "errors are
                    high" sends somebody to find out how high. */}
                {breach.detail}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

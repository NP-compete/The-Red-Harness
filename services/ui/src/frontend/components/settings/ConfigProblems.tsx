import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle } from 'lucide-react';

import {
  readConfigProblems,
  type ConfigProblemReport,
} from '../../services/config-problems-api';

/**
 * Configuration the agent is running despite, not according to.
 *
 * A duplicate key means one of two values is being discarded. The
 * agent started, so nothing draws attention to it, and the log
 * line saying so scrolled past hours ago in a pod that may since
 * have restarted.
 *
 * Shown only when there is something to say. A banner on every
 * healthy deployment is a banner people stop seeing, which costs
 * the one that mattered.
 */
export function ConfigProblems() {
  const { t } = useTranslation();
  const [report, setReport] = useState<ConfigProblemReport | null>(null);

  useEffect(() => {
    let live = true;
    void readConfigProblems().then((found) => {
      if (live) setReport(found);
    });
    return () => {
      live = false;
    };
  }, []);

  if (!report || report.unreadable || report.clean || report.problems.length === 0) {
    return null;
  }

  return (
    <div
      role="alert"
      className="mb-4 rounded-lg border border-amber-500/40 bg-amber-500/5 p-3"
    >
      <div className="flex items-start gap-2">
        <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-500" aria-hidden="true" />
        <div>
          <p className="text-sm font-medium text-foreground">
            {t('configProblems.headline')}
          </p>
          <ul className="mt-2 list-none space-y-1">
            {report.problems.map((problem) => (
              <li key={`${problem.source}:${problem.detail}`} className="text-xs">
                <code className="text-muted-foreground">{problem.source}</code>
                {/* The line number is the value here: "something is
                    wrong with your configuration" sends somebody to
                    read all of it. */}
                <span className="ml-2 text-amber-500/90">{problem.detail}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

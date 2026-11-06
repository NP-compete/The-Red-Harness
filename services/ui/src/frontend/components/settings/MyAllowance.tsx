import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle } from 'lucide-react';

import {
  describeMyAllowance,
  type AllowanceReport,
} from '../../lib/allowance-view';
import { describeForecast, type ForecastView } from '../../lib/forecast-view';
import { readMyAllowance } from '../../services/allowance-api';

/**
 * The month, said only when it is going wrong.
 *
 * A daily allowance is a brake — you wait a day and carry on.
 * A monthly budget is not: running out on the 22nd is a team
 * that cannot work until the 1st, so the warning has to arrive
 * while there is still a month left to change something.
 */
function MonthAhead({ found }: { found: ForecastView }) {
  const { t } = useTranslation();
  const mine = found.whose === 'person';
  const said = found.spent
    ? t(mine ? 'allowance.monthSpent' : 'allowance.monthTeamSpent', {
        limit: found.limit,
      })
    : t(mine ? 'allowance.monthOver' : 'allowance.monthTeamOver', {
        perDay: found.perDay,
        limit: found.limit,
        on: found.exhaustedOn,
      });

  return (
    <p
      role="status"
      data-testid="month-ahead"
      className="mt-1 flex items-center gap-1 text-xs text-amber-500"
    >
      <AlertTriangle className="h-3 w-3 shrink-0" aria-hidden="true" />
      {said}
    </p>
  );
}

/**
 * What this person has left to spend today.
 *
 * Shown before they start something long, rather than
 * discovered by being stopped part-way through it. Absent
 * where nothing is capped: a row saying "spent 1.25 of
 * unlimited" is noise on every page of every deployment that
 * caps nothing.
 */
export function MyAllowance() {
  const { t } = useTranslation();
  const [report, setReport] = useState<AllowanceReport | null | undefined>(undefined);

  useEffect(() => {
    let live = true;
    void readMyAllowance().then((found) => {
      if (live) setReport(found);
    });
    return () => {
      live = false;
    };
  }, []);

  if (report === undefined) return null;
  const described = describeMyAllowance(report);
  if (!described) return null;

  const month = describeForecast(
    report.forecast?.person ?? null,
    report.forecast?.team ?? null,
  );

  return (
    <div className="mt-2">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm text-muted-foreground">{t('allowance.label')}</span>
        {described.person.remaining !== null ? (
          <code className="rounded bg-muted px-2 py-1 text-sm font-medium">
            {t('allowance.left', {
              remaining: described.person.remaining,
              limit: described.person.limit,
            })}
          </code>
        ) : null}
        {described.team?.remaining != null ? (
          <span className="text-xs text-muted-foreground">
            {t('allowance.teamLeft', {
              team: described.teamName,
              remaining: described.team.remaining,
              limit: described.team.limit,
            })}
          </span>
        ) : null}
      </div>
      {described.warn ? (
        <p role="status" className="mt-1 flex items-center gap-1 text-xs text-amber-500">
          <AlertTriangle className="h-3 w-3 shrink-0" aria-hidden="true" />
          {t('allowance.nearlyOut')}
        </p>
      ) : null}
      {month ? <MonthAhead found={month} /> : null}
    </div>
  );
}

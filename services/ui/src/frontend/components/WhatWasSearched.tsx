import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Search } from 'lucide-react';

import { describeSearched, type SearchedRecord } from '../lib/searched-view';

/**
 * What the search weighed, and how well each document matched.
 *
 * Folded away. A table of scores under every answer is noise,
 * and noise is what somebody stops reading before the one that
 * mattered — so the summary line says how many were weighed and
 * how many nearly made it, and the detail waits to be asked
 * for.
 *
 * Separate from the citations above, which name what the answer
 * borrowed from. This names what it considered, including the
 * documents it decided against: "your document was not used"
 * has three possible causes and only one of them leaves a row
 * here.
 */
export function WhatWasSearched({
  searched,
}: {
  searched: SearchedRecord[] | undefined;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const described = describeSearched(searched);
  if (!described) return null;

  return (
    <div className="mt-2" role="group">
      <button
        type="button"
        onClick={() => setOpen((was) => !was)}
        aria-expanded={open}
        className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"
      >
        <Search className="h-3 w-3 shrink-0 opacity-70" aria-hidden="true" />
        {t('searched.summary', {
          count: described.usedCount + described.missedCount,
          weighed: described.usedCount + described.missedCount,
          missed: described.missedCount,
        })}
      </button>
      {open ? (
      <ul className="mt-2 space-y-1">
        {described.rows.map((row) => (
          <li
            key={row.id}
            data-testid={row.used ? `used-${row.id}` : `missed-${row.id}`}
            className="flex items-baseline gap-2 text-xs"
          >
            <span className="tabular-nums text-muted-foreground">{row.match}</span>
            <span className={row.used ? '' : 'text-muted-foreground'}>{row.title}</span>
            {row.used ? null : (
              // Said, not implied by styling alone. Without
              // it the strip reads as a list of sources and
              // somebody goes looking for a quote that is
              // not there.
              <span className="text-muted-foreground">{t('searched.notUsed')}</span>
            )}
          </li>
        ))}
      </ul>
      ) : null}
    </div>
  );
}

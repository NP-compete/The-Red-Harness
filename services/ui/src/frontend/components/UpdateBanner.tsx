import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { RefreshCw } from 'lucide-react';

import { updateDecision } from '../lib/sw-update';

/**
 * Says a new version is ready, and waits to be asked.
 *
 * Two ways to get this wrong, in opposite directions. Taking over
 * on its own loses whatever is on the screen — a half-written
 * message, an interrupt about to be approved. Never mentioning it
 * leaves somebody on a stale version for as long as the tab stays
 * open, which is quieter and therefore the one that happens.
 */
export function UpdateBanner({
  waiting,
  busy,
  onApply,
}: {
  waiting: boolean;
  /** A run is in flight, so the screen has something to lose. */
  busy: boolean;
  onApply: () => void;
}) {
  const { t } = useTranslation();
  const [dismissed, setDismissed] = useState(false);

  const decided = updateDecision({ waiting, busy, dismissed });
  if (decided.action !== 'offer') return null;

  return (
    <div
      role="status"
      className="flex items-center gap-2 border-b border-border bg-secondary/40 px-4 py-2 text-xs"
    >
      <RefreshCw className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
      <span className="text-foreground">{t('update.available')}</span>
      <button
        type="button"
        onClick={onApply}
        className="rounded border border-border px-2 py-0.5 font-medium text-foreground hover:bg-secondary"
      >
        {/* Says what the button does, so the consequence is not a
            surprise on the other side of the click. */}
        {t('update.reload')}
      </button>
      <button
        type="button"
        onClick={() => setDismissed(true)}
        className="text-muted-foreground hover:text-foreground"
      >
        {t('update.later')}
      </button>
    </div>
  );
}

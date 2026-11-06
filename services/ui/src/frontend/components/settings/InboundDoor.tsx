import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle } from 'lucide-react';

import { describeInbound, type InboundReport } from '../../lib/inbound-view';
import { readInbound } from '../../services/schema-version-api';

/**
 * Whether another system may call this agent, and on what terms.
 *
 * Shown only when the door is open. Every deployment has it shut,
 * and a row on every one of them is a row nobody reads — which
 * costs the deployment where it matters.
 */
export function InboundDoor() {
  const { t } = useTranslation();
  const [found, setFound] = useState<InboundReport | null | undefined>(undefined);

  useEffect(() => {
    let live = true;
    void readInbound().then((report) => {
      if (live) setFound(report);
    });
    return () => {
      live = false;
    };
  }, []);

  if (found === undefined) return null;
  const described = describeInbound(found);
  if (!described || !described.open) return null;

  return (
    <div className="mt-2">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm text-muted-foreground">{t('inbound.label')}</span>
        <code className="rounded bg-muted px-2 py-1 text-sm font-medium">
          {t('inbound.open', { mode: described.authMode })}
        </code>
        <span className="text-xs text-muted-foreground">
          {t('inbound.tools', { count: described.publishedTools })}
        </span>
        {described.rate ? (
          <span className="text-xs text-muted-foreground">{described.rate}</span>
        ) : null}
        {described.dailySpend ? (
          <span className="text-xs text-muted-foreground">
            {t('inbound.dailyCap', { amount: described.dailySpend })}
          </span>
        ) : null}
      </div>
      {/* Nothing else on this page says so, and somebody who
          opened this door should know what it answers to a peer
          holding no credential at all. */}
      <p className="mt-1 text-xs text-muted-foreground">
        {t('inbound.discovery')}
      </p>
      {described.unlimited ? (
        <p
          role="alert"
          className="mt-1 flex items-center gap-1 text-xs text-amber-500"
        >
          <AlertTriangle className="h-3 w-3 shrink-0" aria-hidden="true" />
          {t('inbound.noCap')}
        </p>
      ) : null}
    </div>
  );
}

import { useTranslation } from 'react-i18next';
import { useEffect, useMemo, useState } from 'react';

import { countEffort } from '../lib/thread-effort';
import { sumUsage, type ThreadUsage } from '../lib/thread-usage';
import { priceTokens } from '../services/rates-api';
import { getThreadTokenUsage } from '../services/token-usage-api';

function money(amount: string, currency: string): string {
  // A fraction of a cent rounded to zero is how a cheap run becomes
  // a free one.
  const decimals = Math.max(2, (amount.split('.')[1] ?? '').replace(/0+$/, '').length);
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(Number(amount));
}

function count(tokens: number): string {
  return tokens >= 1000 ? `${(tokens / 1000).toFixed(1)}k` : String(tokens);
}

/** What this conversation has used. */
export function ThreadTokenUsageLine({
  threadId,
  messages = [],
}: {
  threadId: string;
  messages?: unknown[];
}) {
  const { t } = useTranslation();
  const [recorded, setRecorded] = useState<ThreadUsage | null>(null);
  const [asked, setAsked] = useState(false);
  // What the turns on screen cost, for a deployment that stores no
  // running total of its own.
  const [priced, setPriced] = useState<{ cost: string | null; currency: string } | null>(null);

  useEffect(() => {
    let alive = true;
    setAsked(false);
    void getThreadTokenUsage(threadId).then((found) => {
      if (!alive) return;
      setRecorded(found ? { ...found, cacheRead: 0 } : null);
      setAsked(true);
    });
    return () => {
      alive = false;
    };
  }, [threadId]);

  // Every answer carries its own count, so a deployment that keeps no
  // running total still has one — for the turns on screen, at least.
  const counted = useMemo(() => sumUsage(messages), [messages]);
  const effort = useMemo(() => countEffort(messages), [messages]);
  const usage = recorded ?? counted;

  // Asked only when the agent kept no priced total of its own.
  const unpricedTotal = asked && recorded?.cost == null ? counted : null;
  useEffect(() => {
    if (!unpricedTotal) return;
    let alive = true;
    void priceTokens(unpricedTotal.inputTokens, unpricedTotal.outputTokens).then((found) => {
      if (alive) setPriced(found);
    });
    return () => {
      alive = false;
    };
  }, [unpricedTotal?.inputTokens, unpricedTotal?.outputTokens, unpricedTotal]);

  // Nothing is said until the agent has been asked: its own total
  // outranks this one, and a figure that jumps when it arrives is
  // worse than a figure that appears a moment late.
  if (!asked || !usage) {
    return null;
  }

  // The compact line reads as punctuation out loud, so the spoken
  // version is spelled out instead of hidden: this was the only place
  // saying what a conversation cost, and it was saying it to nobody
  // who could not see it.
  // Only what a price list priced: an unpriced run says nothing
  // about money rather than saying zero.
  const valued = recorded?.cost != null ? recorded : priced;
  const cost = valued?.cost != null ? money(valued.cost, valued.currency ?? 'USD') : '';

  const spoken = [
    `${usage.used} tokens used`,
    cost ? `costing ${cost}` : '',
    `${usage.inputTokens} sent`,
    `${usage.outputTokens} received`,
    usage.cacheRead > 0 ? `${usage.cacheRead} read from cache` : '',
    effort ? t('counts.modelCalls', { count: effort.modelCalls }) : '',
    effort && effort.toolCalls > 0
      ? t('counts.toolCalls', { count: effort.toolCalls })
      : '',
  ]
    .filter(Boolean)
    .join(', ');

  return (
    <div
      role="note"
      aria-label={spoken}
      className="pl-11 mt-1 text-[11px] text-muted-foreground"
    >
      <span aria-hidden="true">
      {t('chat.tokenBreakdown', {
        used: count(usage.used),
        input: count(usage.inputTokens),
        output: count(usage.outputTokens),
      })}
      {cost && ` · ${cost}`}
      {usage.cacheRead > 0 && ` · ${count(usage.cacheRead)} cached`}
      {effort &&
        ` · ${t('counts.modelCalls', { count: effort.modelCalls })}`}
      {effort && effort.toolCalls > 0 &&
        ` · ${t('counts.toolCalls', { count: effort.toolCalls })}`}
      </span>
    </div>
  );
}

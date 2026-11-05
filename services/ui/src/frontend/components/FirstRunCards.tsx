import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

import { useFirstRunSteps } from '../hooks/useFirstRunSteps';
import { presentFirstRun } from '../lib/first-run-view';

/**
 * What a new workspace could do next, under the composer.
 *
 * An empty screen with a prompt box answers "what do I type" with
 * nothing. These are offers and not a checklist: there is no step
 * to clear before working, and each one disappears on its own once
 * it is done.
 */
export function FirstRunCards({
  chats,
  onAsk,
}: {
  chats: number;
  /** Puts a starting question in the composer, rather than sending one. */
  onAsk: () => void;
}) {
  const { t } = useTranslation();
  const outstanding = useFirstRunSteps({ chats });
  const shown = presentFirstRun(outstanding);

  if (!shown) return null;

  return (
    <section className="w-full text-left" aria-label={t('firstRun.headline', { count: shown.count })}>
      <p className="mb-2 text-sm text-muted-foreground">
        {t('firstRun.headline', { count: shown.count })}
      </p>
      <ul className="grid gap-2 sm:grid-cols-2 list-none p-0">
        {shown.cards.map((card) => (
          <li key={card.step} className="rounded-lg border border-border bg-card p-3">
            <p className="text-sm font-medium text-foreground">{t(card.title)}</p>
            <p className="mt-0.5 text-xs text-muted-foreground">{t(card.detail)}</p>
            {card.step === 'ask_something' ? (
              <button
                type="button"
                onClick={onAsk}
                className="mt-2 text-xs text-primary hover:underline"
              >
                {t(card.action)}
              </button>
            ) : (
              <Link
                to="/settings?tab=personalisation"
                className="mt-2 inline-block text-xs text-primary hover:underline"
              >
                {t(card.action)}
              </Link>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

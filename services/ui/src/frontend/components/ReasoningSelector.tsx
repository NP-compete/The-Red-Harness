import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import {
  chooseFor,
  chosenFor,
  offerIsWorthMaking,
  type ReasoningProfile,
} from '../lib/reasoning-choice';

interface ReasoningSelectorProps {
  threadId: string;
  offered: ReasoningProfile[];
  onChoose: (name: string) => void;
}

/**
 * How carefully to answer this conversation.
 *
 * Absent unless the agent says the options would actually send
 * different requests. A menu whose entries all do the same thing
 * is worse than no menu: somebody picks the careful-sounding one
 * and waits, believing something is happening.
 *
 * The empty value is the agent's own default, and it is where a
 * new conversation starts — which is what happened before this
 * control existed, and the right thing to keep happening for
 * anybody who does not care.
 */
export function ReasoningSelector({ threadId, offered, onChoose }: ReasoningSelectorProps) {
  const { t } = useTranslation();
  const [chosen, setChosen] = useState('');

  useEffect(() => {
    setChosen(chosenFor(threadId, offered) ?? '');
  }, [threadId, offered]);

  if (!offerIsWorthMaking(offered)) return null;

  return (
    <label className="inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap text-xs text-muted-foreground">
      <span>{t('reasoning.label')}</span>
      <select
        className="rounded-md border border-border bg-card px-1.5 py-0.5 text-xs text-foreground"
        value={chosen}
        onChange={(e) => {
          const picked = e.target.value;
          setChosen(picked);
          chooseFor(threadId, picked);
          onChoose(picked);
        }}
      >
        <option value="">{t('reasoning.agentDefault')}</option>
        {offered.map((one) => (
          <option key={one.name} value={one.name}>
            {/* A shipped profile has a written name in the
                catalogue. A deployment's own keeps whatever it
                was called, because nothing here can know about
                it — and inventing a prettier version would mean
                the chooser and the configuration disagreed. */}
            {t(`reasoning.profile${one.name.charAt(0).toUpperCase()}${one.name.slice(1)}`, {
              defaultValue: one.name,
            })}
          </option>
        ))}
      </select>
    </label>
  );
}

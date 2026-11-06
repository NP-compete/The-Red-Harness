import { Alert } from '@patternfly/react-core';
import { useTranslation } from 'react-i18next';

/**
 * Shown between asking the agent to stop and the agent stopping.
 *
 * The stream ends the instant stop is pressed, so without this the
 * composer goes quiet and looks finished while the agent is still
 * working — and whatever that step was about to do, it still does.
 */
export function StoppingNotice({ stopping }: { stopping: boolean }) {
  // Before the early return: a hook has to run on every
  // render, and this component's first act is to not render.
  const { t } = useTranslation();
  if (!stopping) {
    return null;
  }

  return (
    <div className="mx-auto w-full max-w-3xl px-4 pb-2">
      <Alert variant="info" isInline isPlain title={t('chat.stopping')} role="status" aria-live="polite">
        {t('chat.stoppingNote')}
      </Alert>
    </div>
  );
}

import { useTranslation } from 'react-i18next';
import { Alert, AlertActionLink } from '@patternfly/react-core';

import { presentStall } from '../lib/stall-view';
import { useQuietFor } from '../hooks/useQuietFor';

// Below this a pause is the model thinking, not a run in trouble.
const QUIET_SECONDS = 30;

interface StallNoticeProps {
  isLoading: boolean;
  /** Changes whenever something arrives from the run. */
  signature: string;
  toolRunning?: string;
  awaitingPerson?: boolean;
  onStop: () => void;
}

export function StallNotice({
  isLoading,
  signature,
  toolRunning = '',
  awaitingPerson = false,
  onStop,
}: StallNoticeProps) {
  const { t } = useTranslation();
  const quietForSeconds = useQuietFor(isLoading, signature);

  if (!isLoading) {
    return null;
  }

  const state = awaitingPerson
    ? 'waiting'
    : quietForSeconds < QUIET_SECONDS
      ? 'working'
      : toolRunning
        ? 'tool-hung'
        : 'stalled';

  const stall = presentStall({
    state,
    quietForSeconds,
    needsAttention: true,
    reason: '',
    toolRunning,
  });

  if (!stall) {
    return null;
  }

  return (
    <Alert
      variant="warning"
      isInline
      title={t(stall.headline, { count: stall.headlineCount, tool: stall.tool })}
      role="status"
      aria-live="polite"
      actionLinks={<AlertActionLink onClick={onStop}>{t('stall.stopRun')}</AlertActionLink>}
    >
      {stall.note ? t(stall.note, { tool: stall.tool }) : null}
    </Alert>
  );
}

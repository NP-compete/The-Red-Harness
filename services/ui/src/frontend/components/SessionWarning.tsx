import { useTranslation } from 'react-i18next';
import { useEffect, useState } from 'react';
import { Alert } from '@patternfly/react-core';

import { presentSession } from '../lib/session-view';

// Long enough to finish a sentence and send it.
const WARN_WITHIN_MS = 5 * 60_000;

interface SessionWarningProps {
  expiresAt?: Date;
  /** Something half-written that signing out would strand. */
  hasDraft: boolean;
}

/** How long is left, once it is short enough to matter. */
export function SessionWarning({ expiresAt, hasDraft }: SessionWarningProps) {
  const { t } = useTranslation();
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const tick = window.setInterval(() => setNow(new Date()), 30_000);
    return () => window.clearInterval(tick);
  }, []);

  if (!expiresAt) {
    return null;
  }

  const left = expiresAt.getTime() - now.getTime();
  const expired = left <= 0;

  const session = presentSession(
    {
      state: expired ? 'expired' : 'live',
      usable: !expired,
      sessionStillValid: !expired,
      warn: left <= WARN_WITHIN_MS,
      idleAt: expiresAt.toISOString(),
      endsAt: expiresAt.toISOString(),
      reason: 'Your session has ended',
      unsavedWork: hasDraft,
    },
    now,
  );

  if (!session) {
    return null;
  }

  return (
    <Alert
      variant={session.severity === 'high' ? 'danger' : 'warning'}
      isInline
      title={t(session.headline, { count: session.headlineCount })}
      role="status"
      aria-live="polite"
    >
      {session.detail ? t(session.detail) : null}
    </Alert>
  );
}
